"""Summarise the one-technique-at-a-time A/B runs into the figures the dashboard shows on each switch.

    python bench/techniques.py            reads evidence/techniques/<name>/results.json
                                          writes kompactor/static/techniques.json

Each run had a single technique on and everything else off, including compacting earlier, so the figures are
what that technique saves by itself in short sessions. Produced with, for example:

    kompactor prove --tasks bench/tasks.json --repos <folder> --reps 3 --model claude-sonnet-5-5 \\
        --out evidence/techniques/lean --set code_style=lean --set style=off --set bash=false ...
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"trim": "Trim command output", "graph": "Code graph", "lean": "Lean-code rules", "terse": "Short replies"}


def change(base: float, with_: float) -> float:
    return round(100 * (with_ - base) / base, 1) if base else 0.0


def main() -> None:
    out, tasks, meta = {}, set(), {}
    for key in NAMES:
        p = ROOT / "evidence" / "techniques" / key / "results.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        meta = data["meta"]
        runs = data["results"]
        arm = lambda c: [r for r in runs if r["condition"] == c]  # noqa: E731
        b, k = arm("baseline"), arm("kompactor")
        total = lambda rs, f: sum(f(r) for r in rs)  # noqa: E731
        tasks |= {r["task"] for r in runs}
        out[key] = {
            "cost": change(total(b, lambda r: r["cost"]), total(k, lambda r: r["cost"])),
            "tokens": change(total(b, lambda r: r["tokens"]["total"]), total(k, lambda r: r["tokens"]["total"])),
            "output": change(total(b, lambda r: r["tokens"]["output"]), total(k, lambda r: r["tokens"]["output"])),
            "sessions": len(k), "correct": [sum(r["correct"] for r in b), sum(r["correct"] for r in k)],
        }
    doc = {"date": meta.get("date") or time.strftime("%Y-%m-%d"), "model": ", ".join(meta.get("models", [])),
           "reps": meta.get("reps"), "tasks": sorted(tasks), "techniques": out}
    target = ROOT / "kompactor" / "static" / "techniques.json"
    target.write_text(json.dumps(doc, indent=2) + "\n")
    for key, v in out.items():
        print(f"{NAMES[key]:22} cost {v['cost']:+6.1f}%  tokens {v['tokens']:+6.1f}%  output {v['output']:+6.1f}%"
              f"  correct {v['correct'][0]}/{v['sessions']} > {v['correct'][1]}/{v['sessions']}")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
