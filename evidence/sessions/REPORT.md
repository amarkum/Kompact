# Savings by session length

Real headless Claude Code sessions (2.1.308 (Claude Code), claude-sonnet-5-5), Kompactor 0.8.6, 2026-10-22. Every arm ran the same tasks on cobra, flask, click and zustand, 2 run(s) each; Δ is against the same tasks without Kompactor. Technique rows have one technique on (at Balanced strength) and everything else off. The range is a 95% bootstrap interval over the runs; bold rows are clearly different from run-to-run noise (the range excludes 0). Made with `bench/sessions.py`.

## Short sessions (2.3 turns on average without Kompactor)

Without Kompactor: 82,029 tokens and $0.038 per session, 6/6 correct. Tasks: short-go, short-py, short-py2, short-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -1.9% (-3.5 to -0.3, no clear change) | +0.2% | -0.9% | 2.3 | 6/6 |
| Level 2 | -12.2% (-13.6 to -10.7, no clear change) | -10.4% | -16.4% | 2.2 | 6/6 |
| Level 3 | -9.6% (-11.0 to -8.1, no clear change) | -10.1% | -8.3% | 2.2 | 6/6 |
| Level 4 | -9.5% (-10.9 to -8.0, no clear change) | -9.9% | -15.7% | 2.2 | 6/6 |
| Level 5 | -12.2% (-13.6 to -10.7, no clear change) | -10.3% | -19.6% | 2.2 | 6/6 |
| Trim command output only | -12.5% (-13.8 to -11.1, no clear change) | -10.5% | -13.4% | 2.2 | 6/6 |
| Outline-first reads only | +3.1% (+1.3 to +4.9, no clear change) | +10.9% | +9.6% | 2.5 | 6/6 |
| Code graph only | -7.5% (-9.0 to -6.1, no clear change) | -10.3% | -1.8% | 2.2 | 6/6 |
| Lean-code rules only | +0.8% (-6.7 to +8.4, no clear change) | -9.1% | +1.2% | 2.2 | 6/6 |
| Short replies only | +3.5% (-4.4 to +11.5, no clear change) | +1.2% | +2.1% | 2.3 | 6/6 |

## Medium sessions (7.4 turns on average without Kompactor)

Without Kompactor: 214,879 tokens and $0.085 per session, 5/5 correct. Tasks: medium-go, medium-py, medium-py2, medium-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -1.4% (-7.1 to +4.7, no clear change) | -0.3% | -2.0% | 7.8 | 5/5 |
| Level 2 | -6.4% (-9.8 to -2.7, no clear change) | +9.5% | -3.6% | 7.6 | 5/5 |
| Level 3 | +1.0% (-2.7 to +5.0, no clear change) | +16.1% | +9.6% | 8 | 5/5 |
| Level 4 | -7.5% (-11.0 to -3.8, no clear change) | +10.6% | -9.7% | 7.4 | 5/5 |
| Level 5 | +26.4% (+20.6 to +32.6, no clear change) | +43.1% | +14.0% | 9.6 | 5/5 |
| Trim command output only | -5.1% (-9.8 to -0.0, no clear change) | +17.9% | +1.1% | 8 | 5/5 |
| Outline-first reads only | -10.9% (-16.7 to -4.6, no clear change) | -3.9% | -5.0% | 7.8 | 5/5 |
| Code graph only | +3.7% (-3.4 to +11.4, no clear change) | +6.2% | +3.6% | 8.2 | 5/5 |
| Lean-code rules only | +4.9% (-2.5 to +12.9, no clear change) | +8.6% | +4.2% | 7.8 | 5/5 |
| Short replies only | +0.5% (-3.5 to +4.8, no clear change) | +1.6% | +2.2% | 7.6 | 5/5 |

## Long sessions (14 turns on average without Kompactor)

Without Kompactor: 432,962 tokens and $0.149 per session, 2/4 correct. Tasks: long-go, long-py, long-py2, long-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -6.4% (-6.4 to -6.4, no clear change) | -10.8% | -6.5% | 14 | 4/4 |
| Level 2 | -8.6% (-8.6 to -8.6, no clear change) | -2.5% | +0.0% | 13.5 | 3/4 |
| Level 3 | -7.2% (-7.2 to -7.2, no clear change) | -5.7% | -1.7% | 13.8 | 4/4 |
| Level 4 | -15.1% (-15.1 to -15.1, no clear change) | -19.6% | -5.5% | 14 | 4/4 |
| Level 5 | -13.2% (-13.2 to -13.2, no clear change) | -9.0% | -12.8% | 14.2 | 4/4 |
| Trim command output only | -3.0% (-3.0 to -3.0, no clear change) | +10.2% | +7.2% | 13.8 | 4/4 |
| Outline-first reads only | -6.9% (-6.9 to -6.9, no clear change) | -7.9% | -0.6% | 13.5 | 3/4 |
| Code graph only | +7.0% (+7.0 to +7.0, no clear change) | +10.5% | -0.9% | 13.5 | 3/4 |
| Lean-code rules only | -2.4% (-2.4 to -2.4, no clear change) | -2.9% | -3.7% | 14.2 | 3/4 |
| Short replies only | -4.4% (-4.4 to -4.4, no clear change) | -10.8% | -3.7% | 13.8 | 3/4 |

## Very long sessions (25.3 turns on average without Kompactor)

Without Kompactor: 631,522 tokens and $0.221 per session, 2/3 correct. Tasks: xlong-go, xlong-py, xlong-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -1.8% (-1.8 to -1.8, no clear change) | +8.3% | -2.7% | 26 | 3/3 |
| Level 2 | +1.8% (+1.8 to +1.8, no clear change) | +21.1% | -12.1% | 25 | 1/3 |
| Level 3 | +0.2% (+0.2 to +0.2, no clear change) | +23.7% | -7.2% | 25.3 | 2/3 |
| Level 4 | +16.0% (+16.0 to +16.0, no clear change) | +23.9% | +5.7% | 27.7 | 3/3 |
| Level 5 | +5.6% (+5.6 to +5.6, no clear change) | +34.0% | +5.0% | 28.3 | 3/3 |
| Trim command output only | +23.6% (+23.6 to +23.6, no clear change) | +29.8% | +11.9% | 25 | 3/3 |
| Outline-first reads only | -11.6% (-11.6 to -11.6, no clear change) | -15.3% | -13.1% | 26 | 3/3 |
| Code graph only | -2.8% (-2.8 to -2.8, no clear change) | +21.6% | -1.6% | 25.3 | 2/3 |
| Lean-code rules only | +5.3% (+5.3 to +5.3, no clear change) | +34.0% | -8.0% | 26.3 | 2/3 |
| Short replies only | -6.2% (-6.2 to -6.2, no clear change) | +6.5% | -17.7% | 25.3 | 1/3 |
