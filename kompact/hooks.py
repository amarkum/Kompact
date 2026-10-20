"""Claude Code hook handlers. Each reads the hook JSON on stdin and prints a
JSON response (or nothing, which means "carry on unchanged").

Every handler fails open: any exception leaves the tool call untouched.
"""

import json
import os
import sys
import time

from . import config, filters, outline, rules, store, tokens

TEXT_LIMIT = 2_000_000  # don't touch huge/binary files


def _emit(obj) -> None:
    sys.stdout.write(json.dumps(obj))


# ---------------------------------------------------------------------------
# PostToolUse(Bash): compress output before Claude sees it


def post_bash(event: dict, cfg: dict) -> None:
    if not cfg["bash"]:
        return
    resp = event.get("tool_response")
    cmd = (event.get("tool_input") or {}).get("command", "")
    if not isinstance(resp, dict) or "stdout" not in resp or resp.get("isImage"):
        return
    if cmd.lstrip().startswith(("kompact ", "KOMPACT_RAW=1")):
        return
    out, err = resp.get("stdout") or "", resp.get("stderr") or ""
    raw_tokens = tokens.count(out) + tokens.count(err)
    if raw_tokens < cfg["bash_min_tokens"]:
        return
    failed = bool(resp.get("interrupted")) or bool(filters.IMPORTANT.search(err[-2000:] + out[-2000:]))
    code = 1 if failed else 0
    sid = store.stash(cmd, out + ("\n--- stderr ---\n" + err if err else ""))
    new_out = filters.compress(cmd, out, code, stash_id=sid, max_lines=cfg["bash_max_lines"]) if out else ""
    new_err = filters.compress(cmd, err, code, stash_id=sid, max_lines=cfg["bash_max_lines"]) if err else ""
    kept = tokens.count(new_out) + tokens.count(new_err)
    if kept > raw_tokens * 0.9:  # not worth changing what Claude sees
        return
    new_out += f"\n[kompact: {raw_tokens}→{kept} tokens; raw: kompact show {sid}]"
    store.record("bash", raw_tokens, kept, cmd, event.get("session_id", ""))
    _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                  "updatedToolOutput": {**resp, "stdout": new_out, "stderr": new_err}}})


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
    for args in ledger:
        store.record(*args[:4], session=event.get("session_id", ""), force=args[4])
    if reason:
        _deny(reason)


def _pre_read(event: dict, cfg: dict, ledger: list):
    inp = event.get("tool_input") or {}
    path = inp.get("file_path", "")
    session = event.get("session_id", "")
    try:
        st = os.stat(path)
    except OSError:
        return
    if st.st_size > TEXT_LIMIT or os.path.splitext(path)[1].lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp",
                                                                       ".pdf", ".ipynb", ".svg"):
        return
    sig = f"{st.st_mtime_ns}:{st.st_size}:{inp.get('offset')}:{inp.get('limit')}"
    partial = inp.get("offset") is not None or inp.get("limit") is not None

    with store.connect() as db:
        row = db.execute("SELECT sig, state, pending FROM reads WHERE session=? AND path=?", (session, path)).fetchone()

        def put(state, pending=0):
            db.execute("INSERT OR REPLACE INTO reads VALUES (?,?,?,?,?,?)", (session, path, sig, state, pending, time.time()))

        if row is None:
            if cfg["read_outline"] and not partial and os.path.splitext(path)[1] in outline.SOURCE_EXT:
                text = _read(path)
                n = text.count("\n") + 1
                if n >= cfg["read_outline_lines"]:
                    skel = outline.render_outline(path, text)
                    if skel:
                        msg = (f"[kompact] {path} is {n} lines (~{tokens.count(text)} tokens). Outline below "
                               f"(line ranges in brackets). Read only the ranges you need with offset/limit, "
                               f"or call Read again unchanged to get the whole file.\n\n{skel}")
                        raw, kept = tokens.count(text), tokens.count(msg)
                        put("outlined", raw - kept)
                        ledger.append(("read_outline", raw, kept, path, False))
                        return msg
            put("read")
            return

        prev_sig, state, pending = row
        if state == "outlined":
            if not partial:  # Claude wants the whole file after all: undo the claimed saving
                ledger.append(("read_outline", 0, pending, path + " (full read anyway)", True))
            put("read")
            return
        if state == "dup":
            ledger.append(("read_dedupe", 0, pending, path + " (re-read anyway)", True))
            put("read")
            return
        if cfg["read_dedupe"] and prev_sig == sig:
            text = _read(path)
            if partial:
                lines = text.splitlines()
                off = int(inp.get("offset") or 1)
                text = "\n".join(lines[max(off - 1, 0): off - 1 + int(inp.get("limit") or 2000)])
            msg = (f"[kompact] {path} is unchanged since you last read it (same range) in this session; that "
                   f"content is still in your context. If it is not (e.g. after compaction), call Read again.")
            raw, kept = tokens.count(text), tokens.count(msg)
            if raw > kept * 2:
                put("dup", raw - kept)
                ledger.append(("read_dedupe", raw, kept, path, False))
                return msg
        put("read")


def _read(path: str) -> str:
    with open(path, errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Edits invalidate nothing explicitly (the signature includes mtime), but
# compaction and /clear drop file contents from context, so forget reads then.


def reset_reads(event: dict, cfg: dict) -> None:
    with store.connect() as db:
        db.execute("DELETE FROM reads WHERE session=?", (event.get("session_id", ""),))


def session_start(event: dict, cfg: dict) -> None:
    if event.get("source") in ("compact", "clear"):
        reset_reads(event, cfg)
    text = rules.STYLES.get(cfg["style"], "")
    if text:
        _emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})


HANDLERS = {"post-bash": post_bash, "pre-read": pre_read, "pre-compact": reset_reads,
            "session-start": session_start}


def run(name: str) -> int:
    try:
        event = json.load(sys.stdin)
        HANDLERS[name](event, config.load())
    except Exception as e:  # fail open, but leave a trace for `kompact doctor`
        try:
            (store.home() / "hook-errors.log").open("a").write(f"{time.ctime()} {name}: {e!r}\n")
        except OSError:
            pass
    return 0
