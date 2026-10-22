"""A/B by session length: every level, and every technique by itself, against the same sessions without Kompactor.

    python bench/sessions.py --repos <folder> [--reps 2] [--model claude-sonnet-5-5] [--parallel 6]
    python bench/sessions.py --summary      rewrite kompactor/static/techniques.json from the saved runs

Tasks come from bench/sessions.json in four lengths: short (one command and an answer, a few turns), medium
(about five steps), long (ten steps) and very long (twenty steps). A token Kompactor removes early in a session is re-sent
on every later turn, so savings grow with the length of the session. Each run goes through `kompactor prove`'s
run_once: headless `claude -p`, a fresh session and Kompactor data folder, the same prompt, tools, turn limit and
budget cap in every arm. Runs are saved to evidence/sessions/results.json as they finish, and an interrupted
benchmark picks up where it stopped. The summary is what the Configuration page shows for each level and switch.
"""
import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kompactor import __version__, prove  # noqa: E402

# What switching each technique off sets; the same as `off` on the Configuration page's switches.
OFF = {
    "compact": {"compact_window": 0},
    "trim": {"bash": False, "bash_wrap": False},
    "reads": {"read_outline": False, "read_dedupe": False},
    "graph": {"graph": False, "session_map_tokens": 0, "read_graph_context": False},
    "lean": {"code_style": "normal"},
    "terse": {"style": "off"},
}
TECHNIQUES = ["trim", "reads", "graph", "lean", "terse"]


def only(technique: str) -> dict:
    """Balanced settings with every other technique switched off."""
    out = {}
    for t, off in OFF.items():
        if t != technique:
            out.update(off)
    return out


# arm -> (preset, overrides); None is the run without Kompactor
ARMS = {"baseline": None, **{f"level-{p}": (p, {}) for p in range(1, 6)}, **{t: (3, only(t)) for t in TECHNIQUES}}
LENGTHS = ["short", "medium", "long", "xlong"]


def change(base: float, with_: float) -> float:
    return round(100 * (with_ - base) / base, 1) if base else 0.0


def summary(results: list, meta: dict) -> dict:
    """Per session length: each arm's change in cost and tokens against the baseline, over the tasks both ran."""
    lengths = {}
    for length in LENGTHS:
        rs = [r for r in results if r["length"] == length]
        base = [r for r in rs if r["arm"] == "baseline"]
        if not base:
            continue
        mean = lambda xs, f: statistics.mean(f(x) for x in xs)  # noqa: E731
        arms = {}
        for arm in ARMS:
            if arm == "baseline":
                continue
            k = [r for r in rs if r["arm"] == arm]
            tasks = sorted({r["task"] for r in k} & {r["task"] for r in base})
            if not tasks:
                continue
            # per-task means, then summed, so a task with an extra run doesn't weigh more
            tot = lambda xs, f: sum(mean([r for r in xs if r["task"] == t], f) for t in tasks)  # noqa: E731
            b = [r for r in base if r["task"] in tasks]
            kk = [r for r in k if r["task"] in tasks]
            arms[arm] = {
                "cost": change(tot(b, lambda r: r["cost"]), tot(kk, lambda r: r["cost"])),
                "tokens": change(tot(b, lambda r: r["tokens"]["total"]), tot(kk, lambda r: r["tokens"]["total"])),
                "output": change(tot(b, lambda r: r["tokens"]["output"]), tot(kk, lambda r: r["tokens"]["output"])),
                "turns": round(mean(kk, lambda r: r["turns"]), 1),
                "sessions": len(kk), "correct": sum(r["correct"] for r in kk),
            }
        lengths[length] = {
            "turns": round(mean(base, lambda r: r["turns"]), 1),
            "tokens": round(mean(base, lambda r: r["tokens"]["total"])),
            "cost": round(mean(base, lambda r: r["cost"]), 3),
            "sessions": len(base), "correct": sum(r["correct"] for r in base),
            "tasks": sorted({r["task"] for r in base}), "arms": arms,
        }
    return {"date": meta.get("date"), "model": ", ".join(meta.get("models", [])), "reps": meta.get("reps"),
            "claude_version": meta.get("claude_version"), "kompactor_version": meta.get("kompactor_version"),
            "repos": "Flask and zustand", "lengths": lengths}


def report(doc: dict) -> str:
    names = {**{f"level-{p}": f"Level {p}" for p in range(1, 6)}, "trim": "Trim command output only",
             "reads": "Outline-first reads only", "graph": "Code graph only", "lean": "Lean-code rules only",
             "terse": "Short replies only"}
    lines = ["# Savings by session length", "",
             f"Real headless Claude Code sessions ({doc['claude_version']}, {doc['model']}), Kompactor "
             f"{doc['kompactor_version']}, {doc['date']}. Every arm ran the same tasks on {doc['repos']}, "
             f"{doc['reps']} run(s) each; Δ is against the same tasks without Kompactor. Technique rows have one "
             "technique on (at Balanced strength) and everything else off. Made with `bench/sessions.py`.", ""]
    for length, L in doc["lengths"].items():
        lines += [f"## {length.capitalize()} sessions ({L['turns']:g} turns on average without Kompactor)", "",
                  f"Without Kompactor: {L['tokens']:,} tokens and ${L['cost']:.3f} per session, "
                  f"{L['correct']}/{L['sessions']} correct. Tasks: {', '.join(L['tasks'])}.", "",
                  "| Arm | Δ cost | Δ tokens | Δ output tokens | Turns | Correct |", "|---|---:|---:|---:|---:|---:|"]
        for arm, v in L["arms"].items():
            lines.append(f"| {names[arm]} | {v['cost']:+.1f}% | {v['tokens']:+.1f}% | {v['output']:+.1f}% | "
                         f"{v['turns']:g} | {v['correct']}/{v['sessions']} |")
        lines.append("")
    return "\n".join(lines)


def write(out: Path, results: list, meta: dict) -> dict:
    (out / "results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=1))
    doc = summary(results, meta)
    (ROOT / "kompactor" / "static" / "techniques.json").write_text(json.dumps(doc, indent=2) + "\n")
    (out / "REPORT.md").write_text(report(doc))
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tasks", default=str(ROOT / "bench" / "sessions.json"))
    ap.add_argument("--repos", help="folder containing flask/ and zustand/, set up as bench/sessions.json says")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "sessions"))
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--model")
    ap.add_argument("--budget", type=float, default=3.0, help="max USD per run (passed to claude)")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--arms", help="comma-separated arms to run (default: all)")
    ap.add_argument("--only", help="comma-separated task ids")
    ap.add_argument("--summary", action="store_true", help="rewrite the summary from the saved runs, run nothing")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    saved = json.loads((out / "results.json").read_text()) if (out / "results.json").exists() else {}
    results, meta = saved.get("results", []), saved.get("meta", {})
    if a.summary:
        doc = write(out, results, meta)
        print(report(doc))
        return 0
    tasks = json.loads(Path(a.tasks).read_text())["tasks"]
    if a.only:
        tasks = [t for t in tasks if t["id"] in a.only.split(",")]
    arms = a.arms.split(",") if a.arms else list(ARMS)
    meta = {"kompactor_version": __version__, "reps": a.reps, "date": time.strftime("%Y-%m-%d"),
            "claude_version": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()}
    work = out / "runs"
    work.mkdir(exist_ok=True)
    have = {}
    for r in results:
        have[(r["task"], r["arm"])] = have.get((r["task"], r["arm"]), 0) + 1
    # rep-major, arms interleaved, so drift over the hours a run takes affects every arm alike
    jobs = [(t, arm) for rep in range(a.reps) for t in tasks for arm in arms if have.get((t["id"], arm), 0) <= rep]
    planted = {}
    for t in tasks:  # one planted file per repo, shared by its tasks; removed at the end
        for step in t.get("setup", []):
            planted[(t["repo"], step[1])] = step
    for (repo, _), step in planted.items():
        prove._setup(Path(a.repos, repo), [step])
    lock, done = threading.Lock(), [0]

    def run(job):
        t, arm = job
        preset, overrides = ARMS[arm] or (3, {})
        try:
            r = prove.run_once(t, Path(a.repos, t["repo"]).resolve(), "baseline" if arm == "baseline" else "kompactor",
                               work, preset, a.model, a.budget, overrides)
        except Exception as e:  # noqa: BLE001 - one failed run shouldn't stop the benchmark
            print(f"[sessions] {t['id']} · {arm}: {e}", flush=True)
            return
        r.update(arm=arm, length=t["length"])
        with lock:
            results.append(r)
            done[0] += 1
            (out / "results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=1))
            print(f"[sessions] {done[0]}/{len(jobs)} {t['id']} · {arm}: {r['tokens']['total']:,} tokens · "
                  f"${r['cost']:.3f} · {r['turns']} turns · {'correct' if r['correct'] else 'MISSING ' + ', '.join(r['missing'])}",
                  flush=True)

    try:
        with ThreadPoolExecutor(max_workers=max(1, a.parallel)) as pool:
            list(pool.map(run, jobs))
    finally:
        for (repo, _), step in planted.items():
            prove._setup(Path(a.repos, repo), [step], undo=True)
    meta["models"] = sorted({m for r in results for m in r.get("models", [])})
    doc = write(out, results, meta)
    print(report(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
