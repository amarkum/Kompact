"""kompact command line."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__, config, estimate, filters, hooks, outline, store, tokens


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
    out = filters.compress(cmd, raw, p.returncode, stash_id=sid)
    r, k = tokens.count(raw), tokens.count(out)
    store.record("run", r, k, cmd)
    print(out)
    if r > k:
        print(f"[kompact: {r}→{k} tokens; raw: kompact show {sid}]", file=sys.stderr)
    return p.returncode


def cmd_filter(a):
    """Compact stdin as if it were the output of --cmd."""
    raw = sys.stdin.read()
    print(filters.compress(a.cmd or "", raw, a.exit_code))
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
            print(f"  … +{len(hits) - a.max} more (kompact show {sid})")
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


def cmd_hook(a):
    return hooks.run(a.name)


def cmd_gain(a):
    with store.connect() as db:
        rows = db.execute("SELECT feature, COUNT(*), SUM(raw_tokens), SUM(kept_tokens) FROM events GROUP BY feature "
                          "ORDER BY SUM(raw_tokens) - SUM(kept_tokens) DESC").fetchall()
        top = db.execute("SELECT detail, raw_tokens, kept_tokens FROM events WHERE feature='bash' "
                         "ORDER BY raw_tokens - kept_tokens DESC LIMIT 8").fetchall()
    if not rows:
        print("No savings recorded yet. Install the hooks (`kompact install`) and use Claude Code, "
              "or run `kompact estimate` to see what Kompact would have saved on your past sessions.")
        return 0
    tr = sum(r[2] for r in rows)
    tk = sum(r[3] for r in rows)
    print(f"Kompact live savings  (tool output entering Claude's context)\n")
    print(f"  {'feature':<14}{'events':>8}{'before':>10}{'after':>10}{'saved':>9}")
    for f, n, r, k in rows:
        print(f"  {f:<14}{n:>8}{_fmt(r):>10}{_fmt(k):>10}{_pct(r - k, r):>9}")
    print(f"  {'TOTAL':<14}{sum(r[1] for r in rows):>8}{_fmt(tr):>10}{_fmt(tk):>10}{_pct(tr - tk, tr):>9}")
    print(f"\n  {_bar((tr - tk) / tr if tr else 0)}  {_fmt(tr - tk)} tokens kept out of context")
    print("  (each one is also re-sent on every later turn until compaction, so billed savings are larger;"
          " see `kompact estimate`)")
    if top:
        print("\n  biggest wins:")
        for d, r, k in top:
            print(f"    {_fmt(r):>6} → {_fmt(k):<6} {d[:70]}")
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
    print(f"Kompact estimate — replayed {int(s['sessions'])} sessions, {int(s['calls'])} API calls\n")
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
        print("\n  biggest single wins (tokens before → after, Bash):")
        for _, cmd, r, k in sorted(s["top_cmds"], reverse=True)[:6]:
            print(f"    {_fmt(r):>6} → {_fmt(k):<6} {cmd}")
    print("\n  Method: Bash/Read results replayed through Kompact's filters; savings weighted by how many later API"
          "\n  calls would re-send them (cache reads at 0.1×, writes 1.25×, output 5× input price). Read-outline"
          f"\n  assumes {int(estimate.OUTLINE_FOLLOWUP * 100)}% of the file is still read afterwards. Output-style savings are an assumption,"
          "\n  not measured.")
    return 0


# ---------------------------------------------------------------------------


def _hook_entries(exe: str):
    def h(sub):
        return [{"type": "command", "command": f"{exe} hook {sub}", "timeout": 10}]
    return {
        "PostToolUse": [{"matcher": "Bash", "hooks": h("post-bash")}],
        "PreToolUse": [{"matcher": "Read", "hooks": h("pre-read")}],
        "PreCompact": [{"hooks": h("pre-compact")}],
        "SessionStart": [{"hooks": h("session-start")}],
    }


def cmd_install(a):
    target = Path(".claude/settings.json") if a.project else Path.home() / ".claude" / "settings.json"
    exe = shutil.which("kompact") or f"{sys.executable} -m kompact"
    settings = json.loads(target.read_text()) if target.exists() else {}
    hooks_cfg = settings.setdefault("hooks", {})
    for event, entries in _hook_entries(exe).items():
        lst = [e for e in hooks_cfg.get(event, []) if "kompact" not in json.dumps(e)]
        if not a.uninstall:
            lst += entries
        if lst:
            hooks_cfg[event] = lst
        else:
            hooks_cfg.pop(event, None)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"{'Removed' if a.uninstall else 'Installed'} Kompact hooks in {target}")
    if not a.uninstall:
        print("Restart Claude Code (or open /hooks) to pick them up. `kompact gain` shows live savings.")
    return 0


def cmd_config(a):
    if a.key and a.value is not None:
        config.save(a.key, a.value)
    print(json.dumps(config.load(), indent=2))
    return 0


def cmd_doctor(a):
    print(f"kompact {__version__}  python {sys.version.split()[0]}  home {store.home()}")
    print(f"tokenizer: {'tiktoken' if tokens._ENC else 'heuristic (pip install tiktoken for exact counts)'}")
    print(f"sqlite fts5: {'yes' if store.connect().fts else 'no (search falls back to LIKE)'}")
    for p in (Path.home() / ".claude/settings.json", Path(".claude/settings.json")):
        if p.exists():
            print(f"{p}: {'hooks installed' if 'kompact' in p.read_text() else 'no kompact hooks'}")
    log = store.home() / "hook-errors.log"
    if log.exists():
        print("recent hook errors:\n" + "".join(log.read_text().splitlines(True)[-5:]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kompact", description="Cut the tokens Claude Code spends on noise.")
    ap.add_argument("--version", action="version", version=__version__)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("estimate", help="replay past Claude Code sessions and show % Kompact would save")
    p.add_argument("--root", help="transcripts dir (default ~/.claude/projects)")
    p.add_argument("--project", help="only this project folder under the root")
    p.add_argument("--limit", type=int, help="only the N most recent transcripts")
    p.add_argument("--style", choices=["off", "lite", "full"], default="lite")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_estimate)

    p = sp.add_parser("gain", help="live savings recorded by the hooks")
    p.set_defaults(fn=cmd_gain)

    p = sp.add_parser("install", help="add Kompact hooks to Claude Code settings")
    p.add_argument("--project", action="store_true", help="write .claude/settings.json instead of ~/.claude")
    p.add_argument("--uninstall", action="store_true")
    p.set_defaults(fn=cmd_install)

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

    p = sp.add_parser("config", help="show or set config (kompact config style full)")
    p.add_argument("key", nargs="?")
    p.add_argument("value", nargs="?")
    p.set_defaults(fn=cmd_config)

    p = sp.add_parser("hook", help="(internal) Claude Code hook entrypoint")
    p.add_argument("name", choices=list(hooks.HANDLERS))
    p.set_defaults(fn=cmd_hook)

    p = sp.add_parser("doctor", help="check installation")
    p.set_defaults(fn=cmd_doctor)

    a = ap.parse_args(argv)
    if a.cmd == "run" and a.command[:1] == ["--"]:
        a.command = a.command[1:]
    try:
        return a.fn(a) or 0
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
