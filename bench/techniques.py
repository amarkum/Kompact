"""Summarise the one-technique-at-a-time A/B runs in short sessions (evidence/techniques).

    python bench/techniques.py            reads evidence/techniques/<name>/results.json
                                          writes evidence/techniques/summary.json

The Configuration page shows bench/sessions.py's figures, which cover every level and session length.

Each run had a single technique on and everything else off, including compacting earlier, so the figures are
what that technique changes by itself in short sessions. Every run's baseline arm is the same setup, so each
technique is compared with all of them pooled (per task), which is steadier than its own 18. The range is a 95%
bootstrap interval over the runs: when it includes 0, the change isn't clearly different from run-to-run noise.

Produced with, for example:

    kompactor prove --tasks bench/tasks.json --repos <folder> --reps 3 --model claude-sonnet-5-5 \\
        --out evidence/techniques/lean --set code_style=lean --set style=off --set bash=false ...
"""
import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"trim": "Trim command output", "graph": "Code graph", "lean": "Lean-code rules", "terse": "Short replies"}
METRICS = {"cost": lambda r: r["cost"], "tokens": lambda r: r["tokens"]["total"], "output": lambda r: r["tokens"]["output"]}


def change(base: dict, arm: dict, f, pick=lambda rs: rs) -> float:
    """% change of the arm's per-task means over the baseline's, summed across tasks."""
    b = sum(statistics.mean(f(r) for r in pick(base[t])) for t in arm)
    k = sum(statistics.mean(f(r) for r in pick(arm[t])) for t in arm)
    return 100 * (k - b) / b if b else 0.0


def main(resamples: int = 2000) -> None:
    rng = random.Random(7)
    runs, meta = {}, {}
    for key in NAMES:
        p = ROOT / "evidence" / "techniques" / key / "results.json"
        if p.exists():
            data = json.loads(p.read_text())
            meta, runs[key] = data["meta"], data["results"]
    base = defaultdict(list)
    for rs in runs.values():
        for r in rs:
            if r["condition"] == "baseline":
                base[r["task"]].append(r)
    out = {}
    for key, rs in runs.items():
        arm = defaultdict(list)
        for r in rs:
            if r["condition"] == "kompactor":
                arm[r["task"]].append(r)
        fig = {}
        for name, f in METRICS.items():
            boot = sorted(change(base, arm, f, lambda xs: rng.choices(xs, k=len(xs))) for _ in range(resamples))
            fig[name] = round(change(base, arm, f), 1)
            fig[name + "_range"] = [round(boot[int(0.025 * resamples)], 1), round(boot[int(0.975 * resamples)], 1)]
        lo, hi = fig["cost_range"]
        out[key] = {**fig, "clear": lo > 0 or hi < 0, "sessions": sum(len(v) for v in arm.values()),
                    "correct": sum(r["correct"] for v in arm.values() for r in v)}
    doc = {"date": meta.get("date") or time.strftime("%Y-%m-%d"), "model": ", ".join(meta.get("models", [])),
           "reps": meta.get("reps"), "tasks": sorted(base), "baseline_sessions": sum(len(v) for v in base.values()),
           "techniques": out}
    target = ROOT / "evidence" / "techniques" / "summary.json"
    target.write_text(json.dumps(doc, indent=2) + "\n")
    for key, v in out.items():
        print(f"{NAMES[key]:22} cost {v['cost']:+6.1f}% ({v['cost_range'][0]:+.1f} to {v['cost_range'][1]:+.1f})"
              f"{'' if v['clear'] else ' no clear change'}   tokens {v['tokens']:+6.1f}%   reply tokens {v['output']:+6.1f}%"
              f"   correct {v['correct']}/{v['sessions']}")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
