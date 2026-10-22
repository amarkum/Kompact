"""kompactor command line."""

import argparse
import json
import os
import subprocess
import sys

from . import __version__, config, estimate, filters, hooks, installer, outline, store, tokens


def _bar(frac: float, width: int = 24) -> str:
    frac = max(0.0, min(1.0, frac))
    full = int(frac * width)
    return "█" * full + "░" * (width - full)


def _pct(a, b) -> str:
    return f"{100 * a / b:5.1f}%" if b else "  n/a"


def _fmt(n) -> str:
    n = float(n)
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


# ---------------------------------------------------------------------------


def cmd_run(a):
    """Run a command and print its compacted output (manual use / non-Claude agents)."""
    cmd = " ".join(a.command)
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors="replace")
    raw = p.stdout + (("\n" + p.stderr) if p.stderr else "")
    sid = store.stash(cmd, raw)
    out = filters.compress(cmd, raw, p.returncode, stash_id=sid, opts=config.load(os.getcwd()))
    r, k = tokens.count(raw), tokens.count(out)
    store.record("run", r, k, cmd)
    print(out)
    if r > k:
        print(f"[kompactor: {r}›{k} tokens; full output: kompactor show {sid}]", file=sys.stderr)
    return p.returncode


def cmd_filter(a):
    """Compact stdin as if it were the output of --cmd."""
    raw = sys.stdin.read()
    print(filters.compress(a.cmd or "", raw, a.exit_code, opts=config.load(os.getcwd())))
    return 0


def cmd_show(a):
    row = store.get_stash(a.id)
    if not row:
        print(f"no stashed output #{a.id}", file=sys.stderr)
        return 1
    cmd, out = row
    lines = out.splitlines()
    if a.lines:
        s, _, e = a.lines.partition("-")
        lines = lines[int(s) - 1:int(e or s)]
    print(f"$ {cmd}\n" + "\n".join(lines))
    return 0


def cmd_search(a):
    rows = store.search_stash(a.query)
    if not rows:
        print("no matches")
        return 1
    for sid, cmd, hits in rows:
        print(f"#{sid} $ {cmd[:100]}")
        for n, ln in hits[:a.max]:
            print(f"  {n}: {ln[:200]}")
        if len(hits) > a.max:
            print(f"  … +{len(hits) - a.max} more (kompactor show {sid})")
    return 0


def cmd_outline(a):
    for f in a.files:
        if len(a.files) > 1:
            print(f"{f}:")
        print(outline.render_outline(f))
    return 0


def cmd_map(a):
    print(outline.repo_map(a.root, a.budget, a.depth))
    return 0


def cmd_symbol(a):
    hits = outline.find_symbol(a.name, a.root, a.paths or None)
    if not hits:
        print(f"no definition found for {a.name}", file=sys.stderr)
        return 1
    for f, s, e, src in hits:
        print(f"── {f}:{s}-{e}")
        print(src)
    return 0


def cmd_graph(a):
    from . import graph
    root = config.project_root(a.root or os.getcwd()) or os.getcwd()
    if a.action == "build":
        graph.build(root, quiet=False, full=a.full)
        return 0
    if a.action in ("query", "callers", "deps", "impact") and not a.args:
        print(f"usage: kompactor graph {a.action} <{'words' if a.action == 'query' else 'name or path'}>", file=sys.stderr)
        return 2
    try:
        if a.action == "report":
            print(graph.report(root, a.budget or 1800))
        elif a.action == "query":
            print(graph.query(root, " ".join(a.args), a.budget or 1500))
        elif a.action == "callers":
            print(graph.callers_text(root, a.args[0], a.budget or 1200))
        elif a.action == "deps":
            print(graph.deps_text(root, a.args[0], a.budget or 1200))
        elif a.action == "impact":
            print(graph.impact_text(root, a.args[0], a.budget or 1200))
        elif a.action == "path":
            if len(a.args) != 2:
                print("usage: kompactor graph path <from> <to>", file=sys.stderr)
                return 2
            print(graph.path_text(root, a.args[0], a.args[1]))
        elif a.action == "map":
            graph.ensure(root)
            print(graph.session_map(root, a.budget or 800))
        elif a.action == "unused":
            print(graph.unused_text(root, a.budget or 1500))
        elif a.action == "explain":
            print(graph.explain_text(root, a.args[0] if a.args else "", a.budget or 1200))
        elif a.action == "stats":
            v = graph.viz(root)
            print(json.dumps({k: v[k] for k in ("files", "symbols", "refs", "units", "approx_source_tokens",
                                                "map_tokens", "meta")}, indent=2))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def cmd_hook(a):
    return hooks.run(a.name)


def cmd_gain(a):
    if a.json:
        project = config.project_root(a.project) if a.project else ""
        print(json.dumps({**store.savings(a.price, a.session or "", project), "project_path": project,
                          "paused": store.paused(),
                          "version": __version__}))
        return 0
    with store.connect() as db:
        rows = db.execute("SELECT feature, COUNT(*), SUM(raw_tokens), SUM(kept_tokens) FROM events GROUP BY feature "
                          "ORDER BY SUM(raw_tokens) - SUM(kept_tokens) DESC").fetchall()
        top = db.execute("SELECT detail, raw_tokens, kept_tokens FROM events WHERE feature='bash' "
                         "ORDER BY raw_tokens - kept_tokens DESC LIMIT 8").fetchall()
    if not rows:
        print("No savings recorded yet. Install the hooks (`kompactor install`) and use Claude Code, "
              "or run `kompactor estimate` to see what Kompactor would have saved on your past sessions.")
        return 0
    tr = sum(r[2] for r in rows)
    tk = sum(r[3] for r in rows)
    print("Kompactor live savings  (tool output entering Claude's context)\n")
    print(f"  {'feature':<14}{'events':>8}{'before':>10}{'after':>10}{'saved':>9}")
    for f, n, r, k in rows:
        print(f"  {f:<14}{n:>8}{_fmt(r):>10}{_fmt(k):>10}{_pct(r - k, r):>9}")
    print(f"  {'TOTAL':<14}{sum(r[1] for r in rows):>8}{_fmt(tr):>10}{_fmt(tk):>10}{_pct(tr - tk, tr):>9}")
    print(f"\n  {_bar((tr - tk) / tr if tr else 0)}  {_fmt(tr - tk)} tokens kept out of context")
    print("  (each one is also re-sent on every later turn until compaction, so billed savings are larger;"
          " see `kompactor estimate`)")
    if top:
        print("\n  biggest wins:")
        for d, r, k in top:
            print(f"    {_fmt(r):>6} › {_fmt(k):<6} {d[:70]}")
    return 0


EVIDENCE_URL = "https://github.com/amarkum/kompactor#evidence"


def cmd_status(a):
    """What Kompactor is doing right now, and what to do next. Also what plain `kompactor` prints."""
    st = installer.status()
    cfg = config.load(os.getcwd())
    level = f"{config.PRESETS[cfg['preset']]['name']} (level {cfg['preset']} of 5)"
    on = (st["plugin_enabled"] or st["hooks_installed"]) and not store.paused()
    state = ("ON" if on else "STOPPED" if store.paused() else "NOT SET UP")
    print(f"Kompactor {__version__}: {state}")
    if not (st["plugin_enabled"] or st["hooks_installed"]):
        print("  Run `kompactor start` to connect it to Claude Code (CLI and VS Code).")
    elif store.paused():
        print("  Claude Code output passes through untouched. Turn it back on: `kompactor start`")
    else:
        print(f"  Connected via {'the Claude Code plugin' if st['plugin_enabled'] else st['settings_file']}."
              " New Claude Code sessions are compacted.")
    print(f"  Level: {level}. Change it: `kompactor config preset 1-5`, the dashboard, or /kompactor balanced")
    with store.connect() as db:
        raw, kept, n = db.execute("SELECT COALESCE(SUM(raw_tokens),0), COALESCE(SUM(kept_tokens),0), COUNT(*) "
                                  "FROM events").fetchone()
    if n:
        print(f"  Saved so far: {_fmt(raw - kept)} tokens ({_pct(raw - kept, raw)}) over {n} tool calls."
              " Details: `kompactor gain`")
    else:
        print("  Saved so far: nothing yet. Use Claude Code as usual; the status line shows savings per turn.")
    d = _dashboard()
    print(f"  Dashboard: {d['url'] if d else 'not running (`kompactor start` opens it)'}")
    print(f"""
How it works
  Kompactor sits between Claude Code's tools and Claude. Long command output (test runs, installs,
  git log), big file reads and searches are shortened before Claude reads them: errors, failing tests,
  your own stack frames and summary lines are always kept. Claude can still get the full text with
  `kompactor show <id>`. You don't change how you work; just use Claude Code.

Use it from Claude Code
  /kompactor status · /kompactor max savings · /kompactor balanced · /kompactor stop · /kompactor start

Turn it off
  kompactor stop        pause it (settings kept); `kompactor start` resumes
  kompactor uninstall   remove it from Claude Code, VS Code and Cursor, and delete its data

Evidence
  Measured A/B runs of real Claude Code tasks: {EVIDENCE_URL}
  Your own sessions: `kompactor estimate` replays them and shows what it would have saved.

All commands: kompactor --help""")
    return 0


def cmd_estimate(a):
    style_pct = {"off": 0, "lite": 0.10, "full": 0.25}[a.style]
    s = estimate.run(a.root, a.project, a.limit, style_pct)
    if not s["calls"]:
        print("No Claude Code transcripts with usage data found under ~/.claude/projects.")
        return 1
    if a.json:
        print(json.dumps({k: v for k, v in s.items() if k != "top_cmds"}, default=dict, indent=2))
        return 0
    tool, billed, cost = s["tool_tokens"], s["billed"], s["cost"]
    st_cost = s.get("style_cost", 0)
    print(f"Kompactor estimate — replayed {int(s['sessions'])} sessions, {int(s['calls'])} API calls\n")
    print(f"  Tool output in context      {_fmt(tool):>8} tokens  (" +
          ", ".join(f"{k} {_pct(v, tool).strip()}" for k, v in sorted(s['tool_by_name'].items(), key=lambda x: -x[1])[:4])
          + ")")
    print(f"  Total billed tokens         {_fmt(billed):>8}  (input + cache write + cache read + output)")
    print()
    print(f"  Tool-output tokens removed  {_fmt(s['saved_tool']):>8}  {_bar(s['saved_tool'] / tool if tool else 0)} {_pct(s['saved_tool'], tool)}")
    print(f"  Billed tokens saved         {_fmt(s['saved_billed']):>8}  {_bar(s['saved_billed'] / billed)} {_pct(s['saved_billed'], billed)}")
    print(f"  Cost saved (context)        {'':>8}  {_bar(s['saved_cost'] / cost)} {_pct(s['saved_cost'], cost)}")
    if st_cost:
        tot = s["saved_cost"] + st_cost
        print(f"  + output style '{a.style}' (assumed −{int(style_pct * 100)}% output){'':>1}  {_bar(tot / cost)} {_pct(tot, cost)}  total cost")
    print("\n  by feature (billed tokens saved):")
    for f, v in sorted(s["by_feature"].items(), key=lambda x: -x[1]):
        print(f"    {f:<18}{int(s['count_feature'][f]):>6}×  {_fmt(v):>8}  {_pct(v, billed)}")
    if s["top_cmds"]:
        print("\n  biggest single wins (tokens before › after, Bash):")
        for _, cmd, r, k in sorted(s["top_cmds"], reverse=True)[:6]:
            print(f"    {_fmt(r):>6} › {_fmt(k):<6} {cmd}")
    print("\n  Method: Bash/Read results replayed through Kompactor's filters; savings weighted by how many later API"
          "\n  calls would re-send them (cache reads at 0.1×, writes 1.25×, output 5× input price). Read-outline"
          f"\n  assumes {int(estimate.OUTLINE_FOLLOWUP * 100)}% of the file is still read afterwards. Output-style savings are an assumption,"
          "\n  not measured.")
    return 0


# ---------------------------------------------------------------------------


def cmd_install(a):
    target = installer.install("project" if a.project else "user", statusline=not a.no_statusline,
                               uninstall=a.uninstall, shell_prefix=not a.no_shell_prefix)
    print(f"{'Removed' if a.uninstall else 'Installed'} Kompactor hooks in {target}")
    if not a.uninstall:
        print("New Claude Code sessions (CLI and VS Code) will use them. Settings: `kompactor ui`.")
        _prefix_note(installer.status())
    return 0


def _prefix_note(st):
    note = {"kompactor": "Shell prefix: on (failing tests and builds are compacted too)",
            "other": "Shell prefix: another tool already sets CLAUDE_CODE_SHELL_PREFIX, so failing commands are "
                     "not compacted",
            "missing": "Shell prefix: its script is missing; run `kompactor start` again",
            "none": "Shell prefix: off (only commands that succeed are compacted)"}[st["shell_prefix"]]
    print(f"  {note}")


def _path_note(link):
    if link:
        where = os.path.dirname(link).replace(os.path.expanduser("~"), "~", 1)
        print(f"  Added the `kompactor` command to {where}, so it works in any terminal.")


def _pidfile():
    return store.home() / "dashboard.json"


def _dashboard():
    """{pid, url} of the running background dashboard, or None."""
    try:
        d = json.loads(_pidfile().read_text())
        os.kill(d["pid"], 0)
        return d
    except (OSError, ValueError, KeyError, TypeError):
        _pidfile().unlink(missing_ok=True)
        return None


def _kill_dashboard() -> bool:
    d = _dashboard()
    if d:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(d["pid"])], capture_output=True)
            else:
                import signal
                os.kill(d["pid"], signal.SIGTERM)
        except OSError:
            pass
    _pidfile().unlink(missing_ok=True)
    return bool(d)


def cmd_start(a):
    """Turn Kompactor on: connect it to Claude Code (hooks, status line, shell prefix), make the
    `kompactor` command reachable, and run the dashboard in the background on a free port.
    Returns at once; running it again is safe."""
    (store.home() / "paused").unlink(missing_ok=True)
    before = installer.status()
    was_connected = before["plugin_enabled"] or before["hooks_installed"]
    installer.install(statusline=config.read_file()["general"].get("statusline", True))
    st = installer.status()
    print("✓ Kompactor is on: new Claude Code sessions are compacted.")
    where = st["settings_file"].replace(os.path.expanduser("~"), "~", 1)
    print(f"  Connected via {'the Claude Code plugin' if st['plugin_enabled'] else where}")
    _prefix_note(st)
    _path_note(installer.link_on_path())
    if not a.no_editor:
        added = installer.install_editor_extension()
        if added:
            print(f"  Added the Kompactor extension to {' and '.join(added)}: reload the window to see its sidebar.")
    d = _dashboard()
    if not d:
        from . import server
        port = server._free_port(a.port) if a.port else 0
        if port == 0:
            import socket
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
        launch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_launch.py")
        kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        proc = subprocess.Popen([sys.executable, launch, "ui", "--port", str(port), "--no-browser", "--exact-port"], **kw)
        d = {"pid": proc.pid, "url": f"http://127.0.0.1:{port}/"}
        _pidfile().write_text(json.dumps(d))
    print(f"  Dashboard: {d['url']}  (stop with `kompactor stop`)")
    if not was_connected:
        print("  Restart Claude Code so sessions that are already open use it too.")
    if not a.no_browser:
        import webbrowser
        webbrowser.open(d["url"])
    return 0


def cmd_stop(a):
    """Pause compaction everywhere and stop the dashboard. Settings stay; `kompactor start` resumes."""
    (store.home() / "paused").write_text("")
    was = _kill_dashboard()
    print("✓ Kompactor stopped: Claude Code output now passes through untouched."
          + (" Dashboard closed." if was else ""))
    print("  Resume with `kompactor start`; remove completely with `kompactor uninstall`.")
    return 0


def cmd_uninstall(a):
    """Stop, remove hooks / status line / shell prefix / skill / editor extension, and delete Kompactor's data."""
    _kill_dashboard()
    target = installer.install(uninstall=True)
    print(f"✓ Removed Kompactor from {target}")
    removed = installer.uninstall_editor_extension()
    if removed:
        print(f"  Removed the Kompactor extension from {' and '.join(removed)}.")
    if a.keep_data:
        (store.home() / "paused").unlink(missing_ok=True)
        print("  Kept savings history and settings in ~/.kompactor.")
    else:
        import shutil
        shutil.rmtree(store.home(), ignore_errors=True)
        print("  Deleted Kompactor's data: savings history, settings, code graphs and saved outputs (~/.kompactor).")
    if installer.status()["plugin_enabled"]:
        print("  The Claude Code plugin is still enabled; run: claude plugin uninstall amarkum@kompactor")
    print("  Installed it as a Python package? Remove that too, with the tool you installed it with (pip, pipx or uv).")
    return 0


def cmd_ui(a):
    from . import server
    server.serve(a.port, open_browser=not a.no_browser, exact=a.exact_port)
    return 0


def cmd_statusline(a):
    """Claude Code statusLine command: one line of running savings for this session."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    if store.paused():
        print("Kompactor · stopped (kompactor start)")
        return 0
    sid = event.get("session_id", "")
    ctx = (event.get("context_window") or {}).get("total_input_tokens")
    ctx = int(ctx) if isinstance(ctx, (int, float)) and ctx > 0 else 0
    if sid and ctx:
        store.note_context(sid, ctx)
    cfg = config.load((event.get("workspace") or {}).get("current_dir") or event.get("cwd") or os.getcwd())
    name = config.PRESETS[cfg["preset"]]["name"]
    tot = store.session_totals(sid) if sid else {}
    if tot.get("saved", 0) > 0:
        parts = [f"Kompactor −{hooks._fmt(tot['saved'])}"]
        ctx = ctx or tot["context"]
        if ctx and tot["in_context_saved"] > 0:
            parts.append(f"ctx −{100 * tot['in_context_saved'] / (ctx + tot['in_context_saved']):.0f}%")
        if tot["last_turn_saved"] > 0:
            parts.append(f"last turn −{hooks._fmt(tot['last_turn_saved'])}")
        parts.append(name)
        print(" · ".join(parts))
    else:
        print(f"Kompactor · {name}")
    return 0


def cmd_config(a):
    if a.key and a.value is not None:
        try:
            config.save(a.key, a.value)
        except (KeyError, ValueError) as e:
            print(f"unknown or invalid setting: {e}", file=sys.stderr)
            return 1
    eff = config.load(os.getcwd())
    print(f"preset {eff['preset']} · {config.PRESETS[eff['preset']]['name']}   languages: {', '.join(eff['languages']) or '-'}")
    for k in config.KNOBS:
        print(f"  {k:<20} {eff[k]}")
    print(f"(edit in the dashboard: kompactor ui · file: {config.path()})")
    return 0


def cmd_presets(a):
    from . import server
    data = config.read_file()
    presets = {p: {"name": v["name"], "blurb": v["blurb"]} for p, v in config.PRESETS.items()}
    savings = server.preset_savings()
    if a.json:
        print(json.dumps({"current": data["preset"], "presets": presets, "savings": savings}))
        return 0
    for p, v in presets.items():
        mark = "●" if p == data["preset"] else " "
        print(f" {mark} {p} {v['name']:<12} ≈{savings[p]:>2}% on samples  {v['blurb']}")
    print("Change with `kompactor config preset N` or in the dashboard (`kompactor ui`).")
    return 0


def cmd_doctor(a):
    print(f"kompactor {__version__}  python {sys.version.split()[0]}  home {store.home()}")
    print(f"tokenizer: {'tiktoken' if tokens._ENC else 'heuristic (for exact counts, add the optional tiktoken package)'}")
    with store.connect() as db:
        print(f"sqlite fts5: {'yes' if db.fts else 'no (search falls back to LIKE)'}")
    st = installer.status()
    for k, v in st.items():
        print(f"{k}: {v}")
    log = store.home() / "hook-errors.log"
    if log.exists():
        print("recent hook errors:\n" + "".join(log.read_text().splitlines(True)[-5:]))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["setup"]:  # the old name for `start`; older docs still say it
        argv = ["start"] + ["--no-browser" if x == "--no-ui" else x for x in argv[1:]]
    if argv[:1] == ["prove"]:  # has its own parser
        from . import prove
        return prove.main(argv[1:])
    ap = argparse.ArgumentParser(prog="kompactor", description="Cut the tokens Claude Code spends on noise.")
    ap.add_argument("--version", action="version", version=__version__)
    sp = ap.add_subparsers(dest="cmd")

    p = sp.add_parser("status", help="is it on, your level, savings so far, and how to use it (also: plain `kompactor`)")
    p.set_defaults(fn=cmd_status)

    p = sp.add_parser("start", help="turn Kompactor on: connect it to Claude Code and open the dashboard")
    p.add_argument("--port", type=int, default=0, help="preferred port (default: any free port)")
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--no-editor", action="store_true", help="don't add the extension to VS Code or Cursor")
    p.set_defaults(fn=cmd_start)

    p = sp.add_parser("stop", help="pause Kompactor and close the dashboard (settings are kept)")
    p.set_defaults(fn=cmd_stop)

    p = sp.add_parser("uninstall", help="stop and remove Kompactor from Claude Code settings")
    p.add_argument("--keep-data", action="store_true", help="keep ~/.kompactor (history and settings)")
    p.add_argument("--purge", action="store_true", help=argparse.SUPPRESS)  # the default now; kept for old docs
    p.set_defaults(fn=cmd_uninstall)

    p = sp.add_parser("estimate", help="replay past Claude Code sessions and show %% Kompactor would save")
    p.add_argument("--root", help="transcripts dir (default ~/.claude/projects)")
    p.add_argument("--project", help="only this project folder under the root")
    p.add_argument("--limit", type=int, help="only the N most recent transcripts")
    p.add_argument("--style", choices=["off", "lite", "full"], default="lite")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_estimate)

    p = sp.add_parser("gain", help="live savings recorded by the hooks")
    p.add_argument("--json", action="store_true", help="machine-readable totals with a dollar estimate")
    p.add_argument("--price", type=float, default=3.0, help="input-token price in USD per million (default 3)")
    p.add_argument("--session", help="also report this Claude Code session")
    p.add_argument("--project", help="also report this project folder, with its recent turns")
    p.set_defaults(fn=cmd_gain)

    p = sp.add_parser("ui", help="open the settings & savings dashboard (foreground; see `start`)")
    p.add_argument("--port", type=int, default=7420)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--exact-port", action="store_true", help=argparse.SUPPRESS)
    p.set_defaults(fn=cmd_ui)

    p = sp.add_parser("install", help="add Kompactor hooks to Claude Code settings")
    p.add_argument("--project", action="store_true", help="write .claude/settings.json instead of ~/.claude")
    p.add_argument("--uninstall", action="store_true")
    p.add_argument("--no-statusline", action="store_true")
    p.add_argument("--no-shell-prefix", action="store_true",
                   help="don't set CLAUDE_CODE_SHELL_PREFIX (then commands that fail are not compacted)")
    p.set_defaults(fn=cmd_install)

    p = sp.add_parser("statusline", help="(internal) Claude Code status line")
    p.set_defaults(fn=cmd_statusline)

    p = sp.add_parser("map", help="ranked repo skeleton within a token budget")
    p.add_argument("root", nargs="?", default=".")
    p.add_argument("--budget", type=int, default=4000)
    p.add_argument("--depth", type=int, default=1, help="nesting depth of symbols to include")
    p.set_defaults(fn=cmd_map)

    p = sp.add_parser("outline", help="symbols of a file with line ranges")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_outline)

    p = sp.add_parser("symbol", help="print the source of a definition (Name or Class.method)")
    p.add_argument("name")
    p.add_argument("paths", nargs="*")
    p.add_argument("--root", default=".")
    p.set_defaults(fn=cmd_symbol)

    p = sp.add_parser("run", help="run a command and print compacted output")
    p.add_argument("command", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_run)

    p = sp.add_parser("filter", help="compact stdin")
    p.add_argument("--cmd", help="command that produced the input (picks the filter)")
    p.add_argument("--exit-code", type=int, default=0)
    p.set_defaults(fn=cmd_filter)

    p = sp.add_parser("show", help="print a stashed raw output")
    p.add_argument("id", type=int)
    p.add_argument("--lines", help="e.g. 120-180")
    p.set_defaults(fn=cmd_show)

    p = sp.add_parser("search", help="full-text search across stashed raw outputs")
    p.add_argument("query")
    p.add_argument("--max", type=int, default=15)
    p.set_defaults(fn=cmd_search)

    p = sp.add_parser("config", help="show or set config (kompactor config preset 4); easier: kompactor ui")
    p.add_argument("key", nargs="?")
    p.add_argument("value", nargs="?")
    p.set_defaults(fn=cmd_config)

    p = sp.add_parser("graph", help="code graph: build, report, query, callers, deps, impact, path, map")
    p.add_argument("action", choices=["build", "report", "query", "callers", "deps", "impact", "path", "explain",
                                      "unused", "map", "stats"])
    p.add_argument("args", nargs="*")
    p.add_argument("--root", help="project directory (default: current project)")
    p.add_argument("--budget", type=int, help="max tokens of output")
    p.add_argument("--full", action="store_true", help="rebuild from scratch")
    p.set_defaults(fn=cmd_graph)

    p = sp.add_parser("debt", help="ledger of shortcut:/FIXME/HACK/TODO comments")
    p.add_argument("--root")
    p.set_defaults(fn=lambda a: print(__import__("kompactor.graph", fromlist=["graph"]).debt_text(
        config.project_root(a.root or os.getcwd()) or os.getcwd())) or 0)

    sp.add_parser("prove", help="A/B test: run real Claude Code tasks with and without Kompactor (see --help)")

    p = sp.add_parser("presets", help="list quality-vs-tokens levels")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_presets)

    p = sp.add_parser("hook", help="(internal) Claude Code hook entrypoint")
    p.add_argument("name", choices=list(hooks.HANDLERS))
    p.set_defaults(fn=cmd_hook)

    p = sp.add_parser("doctor", help="check installation")
    p.set_defaults(fn=cmd_doctor)

    a = ap.parse_args(argv)
    if not a.cmd:
        a.fn = cmd_status
    if a.cmd == "run" and a.command[:1] == ["--"]:
        a.command = a.command[1:]
    try:
        return a.fn(a) or 0
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
