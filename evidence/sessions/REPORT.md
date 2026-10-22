# Savings by session length

Real headless Claude Code sessions (2.1.308 (Claude Code), claude-sonnet-5-5), Kompactor 0.8.6, 2026-10-22. Every arm ran the same tasks on cobra, flask, click and zustand, 2 run(s) each; Δ is against the same tasks without Kompactor. Technique rows have one technique on (at Balanced strength) and everything else off. Made with `bench/sessions.py`.

## Short sessions (2.4 turns on average without Kompactor)

Without Kompactor: 84,567 tokens and $0.040 per session, 5/5 correct. Tasks: short-go, short-py, short-py2, short-ts.

| Arm | Δ cost | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -2.6% | +0.2% | -0.9% | 2.4 | 5/5 |
| Level 2 | -13.2% | -10.4% | -19.3% | 2.2 | 5/5 |
| Level 3 | -10.3% | -10.1% | -9.4% | 2.2 | 5/5 |
| Level 4 | -10.5% | -9.9% | -18.0% | 2.2 | 4/4 |
| Level 5 | -13.1% | -10.3% | -22.3% | 2.2 | 4/4 |
| Trim command output only | -13.2% | -10.5% | -14.0% | 2.2 | 4/4 |
| Outline-first reads only | +3.1% | +10.9% | +10.4% | 2.8 | 4/4 |
| Code graph only | -8.3% | -10.3% | -2.5% | 2.2 | 4/4 |
| Lean-code rules only | +6.7% | -8.3% | -0.1% | 2.2 | 4/4 |
| Short replies only | +9.5% | +2.0% | +0.2% | 2.5 | 4/4 |

## Medium sessions (7.8 turns on average without Kompactor)

Without Kompactor: 220,857 tokens and $0.087 per session, 4/4 correct. Tasks: medium-go, medium-py, medium-py2, medium-ts.

| Arm | Δ cost | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | +4.7% | +5.6% | +1.0% | 8 | 4/4 |
| Level 2 | -2.7% | +12.6% | -1.1% | 7.8 | 4/4 |
| Level 3 | +4.9% | +19.3% | +12.2% | 8.2 | 4/4 |
| Level 4 | -4.0% | +13.7% | -7.6% | 7.5 | 4/4 |
| Level 5 | +32.6% | +49.8% | +17.4% | 10.2 | 4/4 |
| Trim command output only | -0.0% | +21.5% | +7.5% | 8.2 | 4/4 |
| Outline-first reads only | -10.2% | -6.3% | -2.3% | 7.8 | 4/4 |
| Code graph only | +4.1% | +6.1% | +6.5% | 8.5 | 4/4 |
| Lean-code rules only | +12.9% | +16.5% | +8.4% | 7.8 | 4/4 |
| Short replies only | +4.8% | +4.3% | +7.0% | 8 | 4/4 |

## Long sessions (14 turns on average without Kompactor)

Without Kompactor: 432,962 tokens and $0.149 per session, 2/4 correct. Tasks: long-go, long-py, long-py2, long-ts.

| Arm | Δ cost | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -6.4% | -10.8% | -6.5% | 14 | 4/4 |
| Level 2 | -8.6% | -2.5% | +0.0% | 13.5 | 3/4 |
| Level 3 | -7.2% | -5.7% | -1.7% | 13.8 | 4/4 |
| Level 4 | -15.1% | -19.6% | -5.5% | 14 | 4/4 |
| Level 5 | -11.3% | +0.2% | -12.7% | 14.7 | 3/3 |
| Trim command output only | -4.8% | +9.3% | +9.4% | 14.3 | 3/3 |
| Outline-first reads only | +0.5% | +0.5% | +2.6% | 13.7 | 2/3 |
| Code graph only | +9.6% | +13.0% | -0.8% | 14.3 | 2/3 |
| Lean-code rules only | -5.6% | -10.9% | -7.4% | 13.7 | 2/3 |
| Short replies only | -2.0% | -4.3% | -5.2% | 14 | 2/3 |

## Very long sessions (26.5 turns on average without Kompactor)

Without Kompactor: 757,209 tokens and $0.246 per session, 1/2 correct. Tasks: xlong-py, xlong-ts.

| Arm | Δ cost | Δ tokens | Δ output tokens | Turns | Correct |
|---|---:|---:|---:|---:|---:|
| Level 1 | -0.6% | +7.5% | -1.3% | 25 | 2/2 |
| Level 2 | -9.0% | -2.1% | -17.1% | 25 | 1/2 |
| Level 3 | -14.9% | -2.6% | -23.8% | 23.5 | 1/2 |
| Level 4 | -12.3% | +0.4% | -29.1% | 24 | 2/2 |
| Level 5 | -13.2% | +5.7% | -12.8% | 25.5 | 2/2 |
| Trim command output only | -8.9% | +5.6% | -9.4% | 23.5 | 2/2 |
| Outline-first reads only | -14.0% | -21.9% | -13.7% | 26 | 2/2 |
| Code graph only | -20.4% | -9.6% | -11.1% | 27 | 0/1 |
| Lean-code rules only | +31.8% | +102.8% | +3.1% | 28 | 1/1 |
| Short replies only | +0.5% | +7.7% | -14.3% | 28 | 0/1 |
