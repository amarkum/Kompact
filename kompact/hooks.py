"""Claude Code hook handlers (used by both the CLI and the VS Code extension,
which share ~/.claude/settings.json). Each reads the hook JSON on stdin and
prints a JSON response, or nothing, meaning "carry on unchanged".

Every handler fails open: any exception leaves the tool call untouched.
"""

import json
import os
import sys
import time

from . import config, filters, graph, installer, langs, outline, rules, store, tokens

TEXT_LIMIT = 2_000_000  # don't touch huge/binary files
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ipynb", ".svg", ".ico", ".zip", ".gz"}


def _emit(obj) -> None:
    sys.stdout.write(json.dumps(obj))


def _fmt(n) -> str:
    n = float(n)
    return f"{n / 1e6:.1f}M" if abs(n) >= 1e6 else f"{n / 1e3:.1f}k" if abs(n) >= 1e3 else f"{n:.0f}"


# ---------------------------------------------------------------------------
# PostToolUse(Bash): compress output before Claude sees it


def post_bash(event: dict, cfg: dict) -> None:
    if not cfg["bash"]:
        return
    resp = event.get("tool_response")
    cmd = (event.get("tool_input") or {}).get("command", "")
    if not isinstance(resp, dict) or "stdout" not in resp or resp.get("isImage"):
        return
    if cmd.lstrip().startswith(("kompact ", "KOMPACT_RAW=1", "~/.kompact/bin/kompact")) or "_launch.py" in cmd:
        return
    words = " ".join(filters.argv0(cmd))
    if any(words.startswith(c.strip()) for c in cfg.get("never_compact", []) if c.strip()):
        return
    out, err = resp.get("stdout") or "", resp.get("stderr") or ""
    if "[kompact: " in out[-400:]:  # already compacted (shell prefix, or hooks registered twice)
        return
    # Claude Code saves outputs over ~30K characters to a file and shows Claude a 2 KB preview of it;
    # hooks get only the head. Compact the whole output instead, and drop the file reference so Claude
    # sees the compacted text rather than the preview.
    full = None
    if resp.get("persistedOutputPath"):
        if filters.classify(cmd) == "view":  # cat/head of a huge file: the preview and saved path serve Claude better
            return
        full = _persisted(resp)
        if full is None:
            return
    shown = None
    if full is not None:
        shown = tokens.count(full[:2048]) + 60
        out = full
    raw_tokens = tokens.count(out) + tokens.count(err)
    if raw_tokens < cfg["bash_min_tokens"]:
        return
    failed = bool(resp.get("interrupted")) or bool(filters.IMPORTANT.search(err[-2000:] + out[-2000:]))
    code = 1 if failed else 0
    sid = store.stash(cmd, out + ("\n--- stderr ---\n" + err if err else ""))
    new_out = filters.compress(cmd, out, code, stash_id=sid, opts=cfg) if out else ""
    new_err = filters.compress(cmd, err, code, stash_id=sid, opts=cfg) if err else ""
    new_out = _fit(new_out, PERSIST_LIMIT) if full is not None else new_out
    kept = tokens.count(new_out) + tokens.count(new_err)
    if kept > raw_tokens * 0.9 and full is None:  # not worth changing what Claude sees
        return
    new_out += f"\n[kompact: {raw_tokens}›{kept} tokens; full output: {installer.cli_name()} show {sid}]"
    store.record("bash", raw_tokens if shown is None else shown, kept, cmd, event.get("session_id", ""),
                 project=cfg["project"])
    resp = {k: v for k, v in resp.items() if k not in ("persistedOutputPath", "persistedOutputSize")}
    _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                  "updatedToolOutput": {**resp, "stdout": new_out, "stderr": new_err}}})


PERSIST_READ = 8_000_000
PERSIST_LIMIT = 25_000  # stay under Claude Code's ~30K-character limit, or it would save our text to a file too


def _persisted(resp: dict):
    path = resp.get("persistedOutputPath")
    if not isinstance(path, str) or not path:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(PERSIST_READ)
    except OSError:
        return None


def _fit(text: str, limit: int) -> str:
    """Keep whole lines from the head (2/3) and tail (1/3) of text within limit characters."""
    if len(text) <= limit:
        return text
    lines = text.split("\n")
    head, tail, size, i, j = [], [], 0, 0, len(lines) - 1
    while i <= j:
        from_head = len(head) < 2 * (len(tail) + 1)
        ln = lines[i] if from_head else lines[j]
        if size + len(ln) + 1 > limit - 80:
            break
        size += len(ln) + 1
        if from_head:
            head.append(ln)
            i += 1
        else:
            tail.append(ln)
            j -= 1
    return "\n".join(head + [f"… {j - i + 1} lines omitted …"] + tail[::-1])


# ---------------------------------------------------------------------------
# PreToolUse(Read): outline-first for big files, dedupe unchanged re-reads
#
# Per (session, file) state machine:
#   (none) --big file--> "outlined" (deny once with outline) --next Read--> "read"
#   (none) ------------> "read" --unchanged re-read--> "dup" (deny once) --next Read--> "read"
# A deny is always followed by an allow on retry, so Claude can never get stuck.


def _deny(reason: str) -> None:
    _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                  "permissionDecisionReason": reason}})


def pre_read(event: dict, cfg: dict) -> None:
    ledger = []  # savings are logged after the reads transaction commits (one writer at a time)
    reason = _pre_read(event, cfg, ledger)
    for feature, raw, kept, detail, force in ledger:
        store.record(feature, raw, kept, detail, event.get("session_id", ""), force=force, project=cfg["project"])
    if reason:
        _deny(reason)


def _pre_read(event: dict, cfg: dict, ledger: list):
    inp = event.get("tool_input") or {}
    path = inp.get("file_path", "")
    session = event.get("session_id", "")
    try:
        st = os.stat(path)
    except OSError:
        return None
    ext = os.path.splitext(path)[1].lower()
    if st.st_size > TEXT_LIMIT or ext in BINARY_EXT:
        return None
    sig = f"{st.st_mtime_ns}:{st.st_size}:{inp.get('offset')}:{inp.get('limit')}"
    partial = inp.get("offset") is not None or inp.get("limit") is not None
    source_ext = set(langs.merged(cfg["languages"], "ext")) | outline.SOURCE_EXT

    with store.connect() as db:
        row = db.execute("SELECT sig, state, pending FROM reads WHERE session=? AND path=?", (session, path)).fetchone()

        def put(state, pending=0):
            db.execute("INSERT OR REPLACE INTO reads VALUES (?,?,?,?,?,?)", (session, path, sig, state, pending, time.time()))

        if row is None:
            if cfg["read_outline"] and not partial and ext in source_ext:
                text = _read(path)
                n = text.count("\n") + 1
                gen = langs.generated_re(cfg["languages"])
                is_gen = bool(gen and gen.search(path))
                if n >= (min(150, cfg["read_outline_lines"]) if is_gen else cfg["read_outline_lines"]):
                    skel = outline.render_outline(path, text)
                    if skel and cfg.get("read_graph_context") and cfg.get("graph") and cfg["project"]:
                        try:
                            ctx = graph.file_context(cfg["project"], path)
                        except Exception:  # the graph is an optional extra
                            ctx = ""
                        if ctx:
                            skel = f"{skel}\n\n{ctx}"
                    if skel:
                        kind = "a generated file" if is_gen else f"{n} lines"
                        msg = (f"[kompact] Not an error: {path} is {kind} (~{tokens.count(text)} tokens), so here is "
                               f"its outline (line ranges in brackets). Read just the ranges you need with offset/limit, "
                               f"or repeat the same Read to get the whole file.\n\n{skel}")
                        raw, kept = tokens.count(text), tokens.count(msg)
                        if raw > kept * 1.5:
                            put("outlined", raw - kept)
                            ledger.append(("read_outline", raw, kept, path, False))
                            return msg
            put("read")
            return None

        prev_sig, state, pending = row
        if state == "outlined":
            if not partial:  # Claude wants the whole file after all: undo the claimed saving
                ledger.append(("read_outline", 0, pending, path + " (full read anyway)", True))
            put("read")
            return None
        if state == "dup":
            ledger.append(("read_dedupe", 0, pending, path + " (re-read anyway)", True))
            put("read")
            return None
        if cfg["read_dedupe"] and prev_sig == sig:
            text = _read(path)
            if partial:
                lines = text.splitlines()
                off = int(inp.get("offset") or 1)
                text = "\n".join(lines[max(off - 1, 0): off - 1 + int(inp.get("limit") or 2000)])
            msg = (f"[kompact] Not an error: {path} is unchanged since you read this range earlier in this session, "
                   f"so it is already in your context. If it is not (e.g. after compaction), repeat the same Read.")
            raw, kept = tokens.count(text), tokens.count(msg)
            if raw > kept * 2:
                put("dup", raw - kept)
                ledger.append(("read_dedupe", raw, kept, path, False))
                return msg
        put("read")
        return None


def _read(path: str) -> str:
    with open(path, errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Session lifecycle and per-turn summary


def _rules(cfg: dict) -> str:
    return rules.build(cfg.get("style", "lite"), cfg.get("code_style", "normal"), installer.cli_name(),
                       plain=bool(cfg.get("bash") and cfg.get("bash_plain") and cfg.get("bash_wrap")
                                  and installer.prefix_active()))


def subagent_start(event: dict, cfg: dict) -> None:
    """Subagents get the same prose and code rules as the main agent (no code map)."""
    if not cfg.get("subagent_rules", True):
        return
    text = rules.build(cfg.get("style", "lite"), cfg.get("code_style", "normal"), installer.cli_name())
    if text:
        _emit({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": text}})


def post_explore(event: dict, cfg: dict) -> None:
    """The first time Claude searches or reads code in a session, add the code map.

    Sessions that only run commands never pay for it."""
    budget = cfg.get("session_map_tokens", 0)
    root = cfg.get("project")
    if budget <= 0 or not cfg.get("graph") or not root or not graph.exists(root):
        return
    if not store.once(event.get("session_id", ""), "code-map"):
        return
    text = graph.session_map(root, budget)
    if text:
        store.record("code_map", 0, 0, root, event.get("session_id", ""), force=True, project=root)
        _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}})


def post_edit(event: dict, cfg: dict) -> None:
    """Claude edited a file: refresh the code graph in the background (incremental, debounced)."""
    if cfg.get("graph") and cfg.get("project") and graph.exists(cfg["project"]):
        graph.ensure(cfg["project"], max_age=20)


def pre_compact(event: dict, cfg: dict) -> None:
    store.mark_compacted(event.get("session_id", ""))


def session_start(event: dict, cfg: dict) -> None:
    if event.get("source") in ("compact", "clear"):
        store.mark_compacted(event.get("session_id", ""))
    elif event.get("source") == "startup":
        store.prune(cfg.get("retention_days", 30))
    parts = [_rules(cfg)]
    root = cfg.get("project")
    if cfg.get("graph") and root and event.get("source") in ("startup", "resume", "clear", "compact", None):
        try:
            graph.ensure(root)  # build or refresh; the map itself is given on first exploration
        except Exception as e:  # never block a session on the graph
            (store.home() / "hook-errors.log").open("a").write(f"{time.ctime()} graph: {e!r}\n")
    text = "\n\n".join(p for p in parts if p)
    if text:
        _emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})


def _context_tokens(transcript_path: str) -> int:
    """Size of the context Claude last saw, from the newest usage block in the transcript."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400_000))
            tail = f.read().decode("utf-8", "replace").splitlines()
    except (OSError, TypeError):
        return 0
    for line in reversed(tail):
        if '"usage"' not in line:
            continue
        try:
            u = json.loads(line).get("message", {}).get("usage", {})
        except ValueError:
            continue
        if u:
            return int(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                       + u.get("cache_creation_input_tokens", 0))
    return 0


def turn_message(turn: dict, totals: dict) -> str:
    parts = []
    if turn["saved"] > 0:
        pct = 100 * turn["saved"] / turn["raw"] if turn["raw"] else 0
        parts.append(f"−{_fmt(turn['saved'])} tokens this turn ({_fmt(turn['raw'])} › {_fmt(turn['kept'])}, −{pct:.0f}%)")
    else:
        parts.append("nothing to trim this turn")
    if totals["saved"] > 0:
        parts.append(f"session −{_fmt(totals['saved'])}")
    ctx, live = totals.get("context", 0), totals.get("in_context_saved", 0)
    if ctx and live > 0:
        parts.append(f"context ≈{100 * live / (ctx + live):.0f}% smaller")
    return "Kompact: " + " · ".join(parts)


def stop(event: dict, cfg: dict) -> None:
    if event.get("stop_hook_active"):
        return
    session = event.get("session_id", "")
    ctx = _context_tokens(event.get("transcript_path", ""))
    turn, totals = store.close_turn(session, cfg["project"], ctx)
    msg = turn_message(turn, totals)
    store.write_live({"ts": time.time(), "session": session, "project": cfg["project"], "preset": cfg["preset"],
                      "preset_name": config.PRESETS[cfg["preset"]]["name"], "turn": turn, "session_totals": totals,
                      "message": msg})
    if cfg.get("turn_summary") and turn["saved"] > 0:
        _emit({"systemMessage": msg})


HANDLERS = {"post-bash": post_bash, "pre-read": pre_read, "pre-compact": pre_compact,
            "session-start": session_start, "stop": stop, "subagent-start": subagent_start, "post-edit": post_edit,
            "post-explore": post_explore}


def run(name: str) -> int:
    try:
        event = json.load(sys.stdin)
        HANDLERS[name](event, config.load(event.get("cwd") or os.getcwd()))
    except Exception as e:  # fail open, but leave a trace for `kompact doctor`
        try:
            with (store.home() / "hook-errors.log").open("a") as f:
                f.write(f"{time.ctime()} {name}: {e!r}\n")
        except OSError:
            pass
    return 0
