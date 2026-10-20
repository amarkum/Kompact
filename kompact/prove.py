"""A/B proof: run the same Claude Code tasks with and without Kompact.

    kompact prove --tasks bench/tasks.json --repos /path/to/checkouts [--reps 1] [--preset 3]

Each task runs through headless `claude -p` in both conditions with identical
prompts, tools, turn limits and budget caps. The only difference is Kompact's
hooks, passed with --settings. Every run gets a fresh session id and its own
Kompact data folder, so no state leaks between runs. Recorded per run: tokens
(input + cache writes + cache reads + output, as Claude Code bills them), cost,
turns, wall time, whether the answer contains the expected facts, and Kompact's
own ledger. Writes results.json and REPORT.md to --out.
"""

import argparse
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import __version__, config, installer


def hook_settings() -> dict:
    cmd = installer.launcher()
    hooks = {}
    for event, matcher, handler in installer.HOOKS:
        entry = {"hooks": [{"type": "command", "command": f"{cmd} hook {handler}", "timeout": 15}]}
        hooks.setdefault(event, []).append({"matcher": matcher, **entry} if matcher else entry)
    return {"hooks": hooks}


def _setup(repo: Path, steps, undo=False):
    for step in steps or []:
        if step[0] == "write":
            p = repo / step[1]
            if undo:
                p.unlink(missing_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(step[2])


def _ledger(home: Path) -> dict:
    db = home / "kompact.db"
    if not db.exists():
        return {"events": 0, "saved": 0, "by_feature": {}}
    with sqlite3.connect(db) as c:
        rows = c.execute("SELECT feature, COUNT(*), SUM(raw_tokens - kept_tokens) FROM events GROUP BY feature").fetchall()
    return {"events": sum(r[1] for r in rows), "saved": sum(r[2] or 0 for r in rows),
            "by_feature": {r[0]: {"count": r[1], "saved": r[2]} for r in rows}}


def _tool_trace(session_id: str) -> list:
    """Tool calls Claude made in a run and how big each result was, from its transcript."""
    files = list(Path.home().glob(f".claude/projects/*/{session_id}.jsonl"))
    if not files:
        return []
    uses, out = {}, []
    for line in files[0].read_text(errors="replace").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message")
        content = m.get("content") if isinstance(m, dict) else None
        for b in content if isinstance(content, list) else []:
            if b.get("type") == "tool_use":
                inp = b.get("input") or {}
                uses[b.get("id")] = (b.get("name"), inp.get("command") or inp.get("file_path") or inp.get("pattern") or "")
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                c = b.get("content")
                text = c if isinstance(c, str) else json.dumps(c)
                name, arg = uses[b["tool_use_id"]]
                out.append({"tool": name, "arg": str(arg)[:160], "result_chars": len(text),
                            "kompact": "[kompact" in text})
    return out


def run_once(task: dict, repo: Path, condition: str, work: Path, preset: int, model=None, budget=1.0) -> dict:
    run_dir = work / f"{task['id']}-{condition}-{uuid.uuid4().hex[:6]}"
    home = run_dir / "kompact"
    home.mkdir(parents=True)
    env = dict(os.environ, KOMPACT_HOME=str(home))
    tools = list(task["tools"])
    session_id = str(uuid.uuid4())
    args = ["claude", "-p", task["prompt"], "--output-format", "json", "--max-turns", str(task.get("max_turns", 10)),
            "--session-id", session_id, "--max-budget-usd", str(budget), "--strict-mcp-config"]
    if condition == "kompact":
        (home / "config.json").write_text(json.dumps({"preset": preset}))
        settings = run_dir / "settings.json"
        settings.write_text(json.dumps(hook_settings()))
        args += ["--settings", str(settings)]
        tools += [f"Bash({installer.cli_name()}:*)"]
    args += ["--allowedTools", ",".join(tools)]
    if model:
        args += ["--model", model]
    t0 = time.time()
    p = subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True, timeout=1200,
                       stdin=subprocess.DEVNULL)
    wall = time.time() - t0
    try:
        data = json.loads(p.stdout)
    except ValueError:
        data = {"is_error": True, "result": (p.stdout or p.stderr)[-500:]}
    if data.get("is_error") and not data.get("num_turns"):
        raise RuntimeError(f"claude failed to start ({task['id']}, {condition}): {(p.stderr or p.stdout)[-300:]}")
    usage = data.get("usage") or {}
    by_model = data.get("modelUsage") or {}
    if by_model:  # includes helper models Claude Code used during the run
        tok = {k: sum(m.get(k, 0) or 0 for m in by_model.values()) for k in
               ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")}
        tokens = {"input": tok["inputTokens"], "output": tok["outputTokens"], "cache_read": tok["cacheReadInputTokens"],
                  "cache_write": tok["cacheCreationInputTokens"]}
    else:
        tokens = {"input": usage.get("input_tokens", 0), "output": usage.get("output_tokens", 0),
                  "cache_read": usage.get("cache_read_input_tokens", 0),
                  "cache_write": usage.get("cache_creation_input_tokens", 0)}
    tokens["total"] = sum(tokens.values())
    answer = data.get("result") or ""
    missing = [e for e in task.get("expect", []) if e.lower() not in answer.lower()]
    return {"task": task["id"], "lang": task.get("lang", ""), "condition": condition, "tokens": tokens,
            "cost": data.get("total_cost_usd", 0) or 0, "turns": data.get("num_turns", 0), "wall_s": round(wall, 1),
            "correct": not missing and not data.get("is_error"), "missing": missing, "error": bool(data.get("is_error")),
            "subtype": data.get("subtype", ""), "models": sorted(by_model), "answer": answer[:1500],
            "tools": _tool_trace(session_id), "kompact": _ledger(home) if condition == "kompact" else None}


def summarize(results: list) -> dict:
    out = {}
    for r in results:
        out.setdefault(r["task"], {"lang": r["lang"], "baseline": [], "kompact": []})[r["condition"]].append(r)
    rows = []
    for task, d in out.items():
        b, k = d["baseline"], d["kompact"]
        if not b or not k:
            continue
        mean = lambda rs, f: statistics.mean(f(r) for r in rs)  # noqa: E731
        rows.append({
            "task": task, "lang": d["lang"], "runs": len(b),
            "base_tokens": mean(b, lambda r: r["tokens"]["total"]), "k_tokens": mean(k, lambda r: r["tokens"]["total"]),
            "base_range": (min(r["tokens"]["total"] for r in b), max(r["tokens"]["total"] for r in b)),
            "k_range": (min(r["tokens"]["total"] for r in k), max(r["tokens"]["total"] for r in k)),
            "base_tool_chars": mean(b, lambda r: sum(t["result_chars"] for t in r.get("tools", []))),
            "k_tool_chars": mean(k, lambda r: sum(t["result_chars"] for t in r.get("tools", []))),
            "base_cost": mean(b, lambda r: r["cost"]), "k_cost": mean(k, lambda r: r["cost"]),
            "base_turns": mean(b, lambda r: r["turns"]), "k_turns": mean(k, lambda r: r["turns"]),
            "base_output": mean(b, lambda r: r["tokens"]["output"]), "k_output": mean(k, lambda r: r["tokens"]["output"]),
            "base_correct": sum(r["correct"] for r in b), "k_correct": sum(r["correct"] for r in k),
            "k_saved_ledger": mean(k, lambda r: (r["kompact"] or {}).get("saved", 0)),
            "k_events": mean(k, lambda r: (r["kompact"] or {}).get("events", 0)),
        })
    return {"rows": rows}


def _pct(a, b):
    return f"{100 * (b - a) / a:+.0f}%" if a else "n/a"


def report_md(results: list, meta: dict) -> str:
    rows = summarize(results)["rows"]
    tb = sum(r["base_tokens"] for r in rows)
    tk = sum(r["k_tokens"] for r in rows)
    cb = sum(r["base_cost"] for r in rows)
    ck = sum(r["k_cost"] for r in rows)
    ob = sum(r["base_output"] for r in rows)
    ok = sum(r["k_output"] for r in rows)
    lines = [
        "# Kompact A/B evidence",
        "",
        f"Real headless Claude Code sessions (`claude -p`, Claude Code {meta.get('claude_version', '?')}, "
        f"model {', '.join(meta.get('models', [])) or 'default'}), Kompact {meta['kompact_version']} at level "
        f"{meta['preset']} ({config.PRESETS[meta['preset']]['name']}). {meta['reps']} run(s) per task and condition; "
        f"same prompt, tools, turn limit and budget cap in both conditions. Generated {meta['date']}.",
        "",
        f"**Total across {len(rows)} tasks: {tb:,.0f} › {tk:,.0f} tokens ({_pct(tb, tk)}), "
        f"cost ${cb:.2f} › ${ck:.2f} ({_pct(cb, ck)}), output tokens {_pct(ob, ok)}. "
        f"Correct answers: {sum(r['base_correct'] for r in rows)}/{sum(r['runs'] for r in rows)} without, "
        f"{sum(r['k_correct'] for r in rows)}/{sum(r['runs'] for r in rows)} with Kompact.**",
        "",
        "| Task | Lang | Tokens without (min–max) | Tokens with (min–max) | Δ tokens | Cost without | Cost with | Δ cost "
        "| Tool output chars | Turns | Correct |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['task']} | {r['lang']} | {r['base_tokens']:,.0f} ({r['base_range'][0] / 1000:.0f}k–"
                     f"{r['base_range'][1] / 1000:.0f}k) | {r['k_tokens']:,.0f} ({r['k_range'][0] / 1000:.0f}k–"
                     f"{r['k_range'][1] / 1000:.0f}k) | {_pct(r['base_tokens'], r['k_tokens'])} | ${r['base_cost']:.3f} | "
                     f"${r['k_cost']:.3f} | {_pct(r['base_cost'], r['k_cost'])} | {r['base_tool_chars'] / 1000:.1f}k › "
                     f"{r['k_tool_chars'] / 1000:.1f}k | {r['base_turns']:.1f} › {r['k_turns']:.1f} | "
                     f"{r['base_correct']}/{r['runs']} › {r['k_correct']}/{r['runs']} |")
    lines += ["", "Tokens = input + cache writes + cache reads + output, summed over every API call in the session "
              "(what Claude Code bills). Δ is relative to the run without Kompact. Correct means the final answer "
              "contained every expected fact (see `bench/tasks.json`).", "",
              "## What happened in each run", "",
              "Tool calls Claude made (from the session transcript), result size, and what Kompact changed.", ""]
    for r in sorted(results, key=lambda r: (r["task"], r["condition"])):
        calls = "; ".join(f"{t['tool']} {t['arg'][:60]} ({t['result_chars']:,} chars{', compacted' if t['kompact'] else ''})"
                          for t in r.get("tools", [])[:6]) or "no tool calls"
        led = ""
        if r["condition"] == "kompact" and r["kompact"]:
            led = " · Kompact: " + (", ".join(f"{f} ×{v['count']} (−{v['saved']:,} tokens)"
                                              for f, v in r["kompact"]["by_feature"].items()) or "nothing to compact")
        lines.append(f"- **{r['task']} · {r['condition']}** ({r['tokens']['total']:,} tokens, {r['turns']} turns): "
                     f"{calls}{led}")
    lines += ["", "## Answers", ""]
    for r in results:
        lines.append(f"<details><summary>{r['task']} · {r['condition']} · "
                     f"{'correct' if r['correct'] else 'missing ' + ', '.join(r['missing'])}</summary>\n\n"
                     f"```\n{r['answer'].strip()[:1200]}\n```\n</details>\n")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kompact prove", description=__doc__.split("\n\n")[0])
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--repos", required=True, help="folder containing the task repos")
    ap.add_argument("--out", default="evidence")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--preset", type=int, default=3)
    ap.add_argument("--only", help="comma-separated task ids")
    ap.add_argument("--model")
    ap.add_argument("--budget", type=float, default=1.0, help="max USD per run (passed to claude)")
    ap.add_argument("--parallel", type=int, default=1, help="tasks to run at the same time")
    a = ap.parse_args(argv)
    tasks = json.loads(Path(a.tasks).read_text())["tasks"]
    if a.only:
        keep = set(a.only.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    out = Path(a.out).resolve()  # claude runs inside each repo, so every path must be absolute
    out.mkdir(parents=True, exist_ok=True)
    work = out / "runs"
    work.mkdir(exist_ok=True)
    results_file = out / "results.json"
    results = json.loads(results_file.read_text())["results"] if results_file.exists() else []
    claude_version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    lock = threading.Lock()
    have = {}
    for r in results:
        have[(r["task"], r["condition"])] = have.get((r["task"], r["condition"]), 0) + 1

    def do_task(task):
        repo = Path(a.repos, task["repo"]).resolve()
        with lock:
            _setup(repo, task.get("setup"))
        try:
            for rep in range(a.reps):
                for condition in ("baseline", "kompact"):  # interleaved so drift affects both equally
                    if have.get((task["id"], condition), 0) > rep:
                        continue
                    r = run_once(task, repo, condition, work, a.preset, a.model, a.budget)
                    with lock:
                        results.append(r)
                        results_file.write_text(json.dumps({"results": results}, indent=1))
                        print(f"[prove] {task['id']} · {condition} · run {rep + 1}: {r['tokens']['total']:,} tokens · "
                              f"${r['cost']:.3f} · {r['turns']} turns · "
                              f"{'correct' if r['correct'] else 'MISSING ' + ', '.join(r['missing'])}", flush=True)
        finally:
            with lock:
                _setup(repo, task.get("setup"), undo=True)

    with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as pool:
        list(pool.map(do_task, tasks))
    meta = {"kompact_version": __version__, "preset": a.preset, "reps": a.reps, "claude_version": claude_version,
            "models": sorted({m for r in results for m in r.get("models", [])}), "date": time.strftime("%Y-%m-%d")}
    results_file.write_text(json.dumps({"meta": meta, "results": results}, indent=1))
    (out / "REPORT.md").write_text(report_md(results, meta))
    print((out / "REPORT.md").read_text().split("\n\n|")[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
