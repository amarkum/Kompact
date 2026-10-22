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

## Long sessions (14.8 turns on average without Kompactor)

Without Kompactor: 411,417 tokens and $0.151 per session, 5/8 correct. Tasks: long-go, long-py, long-py2, long-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -4.9% (-11.9 to +3.1, no clear change) | +1.5% | -5.8% | 14.1 | 7/8 |
| **Level 2** | -8.6% (-14.0 to -2.3) | -0.8% | -1.5% | 13.4 | 7/8 |
| **Level 3** | -7.2% (-12.9 to -0.7) | -0.9% | -2.8% | 13.5 | 7/8 |
| Level 4 | -7.8% (-15.0 to +0.7, no clear change) | -0.6% | -5.0% | 14 | 7/8 |
| **Level 5** | -12.5% (-18.2 to -6.1) | -4.9% | -10.8% | 14.4 | 8/8 |
| Trim command output only | -5.3% (-11.0 to +1.0, no clear change) | +9.5% | +3.2% | 14 | 8/8 |
| **Outline-first reads only** | -7.7% (-14.1 to -0.6) | -4.4% | -6.4% | 13.5 | 6/8 |
| Code graph only | +4.3% (-3.3 to +12.7, no clear change) | +13.8% | +7.9% | 15.5 | 5/8 |
| Lean-code rules only | -1.5% (-7.5 to +5.3, no clear change) | +8.4% | -4.5% | 14.2 | 5/8 |
| Short replies only | -6.1% (-13.0 to +1.7, no clear change) | -11.0% | -9.7% | 13.8 | 7/8 |

## Very long sessions (25.1 turns on average without Kompactor)

Without Kompactor: 636,950 tokens and $0.213 per session, 7/8 correct. Tasks: xlong-go, xlong-py, xlong-py2, xlong-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | +0.3% (-5.3 to +6.3, no clear change) | +2.0% | +2.2% | 26.1 | 8/8 |
| Level 2 | +4.7% (+0.0 to +9.3, no clear change) | +6.3% | -5.7% | 25.5 | 6/8 |
| Level 3 | +7.3% (-1.4 to +16.6, no clear change) | +18.7% | -1.7% | 26.4 | 6/8 |
| **Level 4** | +18.9% (+7.5 to +30.8) | +20.0% | +5.3% | 26.5 | 7/8 |
| Level 5 | +4.9% (-0.9 to +11.3, no clear change) | +18.5% | +1.4% | 27.9 | 8/8 |
| **Trim command output only** | +13.3% (+1.2 to +25.7) | +18.1% | +4.3% | 25.8 | 8/8 |
| **Outline-first reads only** | -7.3% (-13.6 to -0.4) | -9.5% | -9.6% | 25.9 | 8/8 |
| Code graph only | +9.1% (-0.2 to +18.9, no clear change) | +22.6% | -0.6% | 25.6 | 7/8 |
| Lean-code rules only | -4.4% (-13.3 to +4.7, no clear change) | -1.3% | -8.9% | 26.1 | 6/8 |
| Short replies only | -6.9% (-13.3 to +0.1, no clear change) | -1.5% | -13.8% | 24.9 | 6/8 |
