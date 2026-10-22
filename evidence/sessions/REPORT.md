# Savings by session length

Real headless Claude Code sessions (2.1.308 (Claude Code), claude-sonnet-5-5), Kompactor 0.8.6, 2026-10-22. Every arm ran the same tasks on cobra, flask, click and zustand, 2 run(s) each; Δ is against the same tasks without Kompactor. Technique rows have one technique on (at Balanced strength) and everything else off. The range is a 95% bootstrap interval over the runs; bold rows are clearly different from run-to-run noise (the range excludes 0). Made with `bench/sessions.py`.

## Short sessions (2.5 turns on average without Kompactor)

Without Kompactor: 88,502 tokens and $0.040 per session, 8/8 correct. Tasks: short-go, short-py, short-py2, short-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| **Level 1** | -2.4% (-4.4 to -0.3) | -0.2% | -0.6% | 2.5 | 8/8 |
| **Level 2** | -12.3% (-14.2 to -10.4) | -10.8% | -16.5% | 2.2 | 8/8 |
| **Level 3** | -9.4% (-11.3 to -7.5) | -10.5% | -10.9% | 2.2 | 8/8 |
| **Level 4** | -9.8% (-11.8 to -7.8) | -10.3% | -18.9% | 2.2 | 8/8 |
| **Level 5** | -10.9% (-13.3 to -8.3) | -10.5% | -18.5% | 2.2 | 8/8 |
| **Trim command output only** | -12.3% (-14.0 to -10.2) | -10.9% | -11.1% | 2.2 | 8/8 |
| Outline-first reads only | -2.4% (-7.8 to +3.3, no clear change) | -0.2% | +4.1% | 2.5 | 8/8 |
| **Code graph only** | -7.7% (-9.7 to -5.5) | -10.7% | -3.9% | 2.2 | 8/8 |
| Lean-code rules only | +2.4% (-6.5 to +11.4, no clear change) | -4.5% | +2.6% | 2.4 | 8/8 |
| Short replies only | +2.3% (-7.8 to +12.3, no clear change) | -4.3% | -4.4% | 2.4 | 8/8 |

## Medium sessions (7.8 turns on average without Kompactor)

Without Kompactor: 216,224 tokens and $0.085 per session, 8/8 correct. Tasks: medium-go, medium-py, medium-py2, medium-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | +10.9% (-0.3 to +23.6, no clear change) | +13.1% | +4.5% | 8.4 | 8/8 |
| Level 2 | -1.6% (-9.6 to +8.1, no clear change) | +12.7% | -3.9% | 7.6 | 8/8 |
| Level 3 | +5.7% (-3.4 to +16.7, no clear change) | +21.8% | +5.8% | 8.2 | 8/8 |
| Level 4 | +11.3% (-6.9 to +31.3, no clear change) | +19.7% | +11.0% | 8.1 | 8/8 |
| **Level 5** | +19.5% (+1.0 to +39.5) | +39.4% | +4.4% | 9.2 | 8/8 |
| Trim command output only | -0.9% (-9.1 to +9.0, no clear change) | +19.4% | +1.1% | 7.9 | 8/8 |
| Outline-first reads only | -8.9% (-19.7 to +2.9, no clear change) | -3.7% | -6.5% | 7.8 | 8/8 |
| Code graph only | +10.4% (-0.6 to +23.1, no clear change) | +9.5% | +1.1% | 8.2 | 8/8 |
| **Lean-code rules only** | +19.5% (+3.1 to +37.7) | +17.7% | +6.5% | 8.1 | 8/8 |
| Short replies only | +2.0% (-6.8 to +12.3, no clear change) | +8.3% | -3.2% | 7.8 | 8/8 |

## Long sessions (14.3 turns on average without Kompactor)

Without Kompactor: 412,466 tokens and $0.151 per session, 4/7 correct. Tasks: long-go, long-py, long-py2, long-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -5.3% (-12.2 to +2.3, no clear change) | -1.5% | -3.2% | 14.1 | 6/7 |
| Level 2 | -7.3% (-12.9 to -1.1, no clear change) | +0.4% | +2.2% | 13.3 | 6/7 |
| Level 3 | -7.1% (-12.3 to -0.7, no clear change) | -2.2% | -1.2% | 13.4 | 6/7 |
| Level 4 | -8.8% (-15.8 to -1.5, no clear change) | -8.5% | +0.7% | 14.1 | 6/7 |
| Level 5 | -12.9% (-18.2 to -6.9, no clear change) | -6.3% | -6.0% | 14.7 | 7/7 |
| Trim command output only | -3.1% (-8.6 to +3.3, no clear change) | +11.1% | +8.0% | 14 | 7/7 |
| Outline-first reads only | -8.8% (-14.4 to -3.1, no clear change) | -3.8% | -4.4% | 13.3 | 5/7 |
| Code graph only | +5.2% (-2.4 to +13.6, no clear change) | +13.9% | +11.5% | 15.7 | 4/7 |
| Lean-code rules only | +0.1% (-5.8 to +7.1, no clear change) | +9.7% | +0.8% | 14.3 | 5/7 |
| Short replies only | -5.3% (-12.0 to +2.2, no clear change) | -13.7% | -5.4% | 13.7 | 6/7 |

## Very long sessions (25 turns on average without Kompactor)

Without Kompactor: 692,640 tokens and $0.226 per session, 5/6 correct. Tasks: xlong-go, xlong-py, xlong-py2, xlong-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -1.6% (-5.6 to +2.7, no clear change) | +2.5% | -1.0% | 25.7 | 6/6 |
| Level 2 | +3.8% (+1.7 to +6.1, no clear change) | +10.1% | -7.6% | 25.3 | 4/6 |
| Level 3 | +10.5% (+3.4 to +17.9, no clear change) | +31.3% | +1.4% | 26 | 4/6 |
| Level 4 | +11.1% (+8.5 to +13.8, no clear change) | +7.1% | +7.8% | 25.7 | 5/6 |
| Level 5 | +10.7% (+8.3 to +13.2, no clear change) | +35.8% | +3.2% | 27.4 | 5/5 |
| Trim command output only | +24.8% (+20.8 to +29.0, no clear change) | +29.6% | +13.3% | 26.2 | 5/5 |
| Outline-first reads only | -6.9% (-11.4 to -2.3, no clear change) | -11.8% | -6.3% | 26.2 | 5/5 |
| Code graph only | +0.5% (-4.2 to +5.3, no clear change) | +11.6% | +3.3% | 25.8 | 4/5 |
| Lean-code rules only | -4.8% (-12.1 to +2.9, no clear change) | +3.2% | -10.3% | 26.4 | 4/5 |
| Short replies only | -3.1% (-5.2 to -0.9, no clear change) | +7.6% | -13.2% | 25.4 | 3/5 |
