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

## Medium sessions (7.7 turns on average without Kompactor)

Without Kompactor: 210,148 tokens and $0.083 per session, 6/6 correct. Tasks: medium-go, medium-py, medium-py2, medium-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | +6.4% (-3.6 to +17.4, no clear change) | +4.0% | -1.3% | 7.8 | 6/6 |
| Level 2 | -2.0% (-9.8 to +7.3, no clear change) | +13.0% | -3.0% | 7.5 | 6/6 |
| Level 3 | +5.7% (-2.7 to +15.8, no clear change) | +19.9% | +8.7% | 7.8 | 6/6 |
| Level 4 | -3.4% (-11.1 to +5.7, no clear change) | +14.1% | -9.9% | 7.3 | 6/6 |
| Level 5 | +32.5% (+21.9 to +45.0, no clear change) | +47.9% | +12.2% | 9.2 | 6/6 |
| Trim command output only | -0.1% (-8.5 to +9.8, no clear change) | +21.8% | +2.3% | 7.8 | 6/6 |
| Outline-first reads only | -5.8% (-13.6 to +4.1, no clear change) | -0.7% | -4.2% | 7.7 | 6/6 |
| Code graph only | +8.6% (-0.1 to +18.9, no clear change) | +9.7% | +2.9% | 8.2 | 5/5 |
| Lean-code rules only | +9.8% (+1.1 to +20.2, no clear change) | +12.1% | +3.5% | 7.8 | 5/5 |
| Short replies only | +5.2% (-3.2 to +15.2, no clear change) | +5.0% | +1.5% | 7.6 | 5/5 |

## Long sessions (14.2 turns on average without Kompactor)

Without Kompactor: 429,880 tokens and $0.147 per session, 3/5 correct. Tasks: long-go, long-py, long-py2, long-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -5.9% (-6.4 to -5.4, no clear change) | -9.6% | -6.2% | 14 | 4/4 |
| Level 2 | -8.1% (-8.6 to -7.5, no clear change) | -1.2% | +0.3% | 13.5 | 3/4 |
| Level 3 | -6.7% (-7.2 to -6.1, no clear change) | -4.4% | -1.4% | 13.8 | 4/4 |
| Level 4 | -14.6% (-15.1 to -14.1, no clear change) | -18.5% | -5.2% | 14 | 4/4 |
| Level 5 | -12.7% (-13.2 to -12.2, no clear change) | -7.8% | -12.5% | 14.2 | 4/4 |
| Trim command output only | -2.5% (-3.0 to -1.9, no clear change) | +11.7% | +7.5% | 13.8 | 4/4 |
| Outline-first reads only | -6.4% (-6.9 to -5.9, no clear change) | -6.7% | -0.3% | 13.5 | 3/4 |
| Code graph only | +7.6% (+7.0 to +8.2, no clear change) | +12.0% | -0.6% | 13.5 | 3/4 |
| Lean-code rules only | -1.9% (-2.4 to -1.3, no clear change) | -1.6% | -3.4% | 14.2 | 3/4 |
| Short replies only | -3.8% (-4.4 to -3.3, no clear change) | -9.5% | -3.4% | 13.8 | 3/4 |

## Very long sessions (25.2 turns on average without Kompactor)

Without Kompactor: 559,054 tokens and $0.208 per session, 3/4 correct. Tasks: xlong-go, xlong-py, xlong-py2, xlong-ts.

| Arm | Δ cost (95% range) | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -1.6% (-1.6 to -1.6, no clear change) | +6.9% | -2.7% | 25.8 | 4/4 |
| Level 2 | +4.6% (+4.6 to +4.6, no clear change) | +19.5% | -10.2% | 25 | 2/4 |
| Level 3 | +5.8% (+5.8 to +5.8, no clear change) | +30.1% | -4.3% | 26 | 3/4 |
| Level 4 | +16.0% (+16.0 to +16.0, no clear change) | +23.9% | +5.7% | 27.7 | 3/3 |
| Level 5 | +5.6% (+5.6 to +5.6, no clear change) | +34.0% | +5.0% | 28.3 | 3/3 |
| Trim command output only | +23.6% (+23.6 to +23.6, no clear change) | +29.8% | +11.9% | 25 | 3/3 |
| Outline-first reads only | -11.6% (-11.6 to -11.6, no clear change) | -15.3% | -13.1% | 26 | 3/3 |
| Code graph only | -2.8% (-2.8 to -2.8, no clear change) | +21.6% | -1.6% | 25.3 | 2/3 |
| Lean-code rules only | +5.3% (+5.3 to +5.3, no clear change) | +34.0% | -8.0% | 26.3 | 2/3 |
| Short replies only | -6.2% (-6.2 to -6.2, no clear change) | +6.5% | -17.7% | 25.3 | 1/3 |
