# Evidence

Every number here comes from real headless Claude Code sessions (`claude -p`) on public repos, run with
`kompact prove`. Each task runs three times without Kompact and three times with it, using the same prompt,
tools, turn limit and budget cap. The two arms run interleaved, so model drift affects both equally.

- [`REPORT.md`](REPORT.md) is the main result: 9 tasks, 54 sessions, Kompact at level 3 (Balanced),
  installed as a plugin (hooks and the `/kompact` skill) with the shell prefix on, as `kompact setup` leaves it.
  [`results.json`](results.json) has every session: tokens by type, cost, turns, the answer, each tool
  call with its result size, and Kompact's own ledger.
- [`EXAMPLE.md`](EXAMPLE.md) shows, side by side, what Claude received for the same failing vitest run
  without Kompact (15,617 characters, mostly passing tests) and with it (724 characters, exit code kept).
- [`levels/level-1`](levels/level-1/REPORT.md) and [`levels/level-5`](levels/level-5/REPORT.md) re-run the same
  27 Kompact sessions at Max quality and Max savings against the same baselines: −4% and −15% tokens,
  −6% and −11% cost, 27/27 correct at both ends (Balanced: −11% tokens, −8% cost).
- [`experiments/plain-without-prefix`](experiments/plain-without-prefix/REPORT.md) and
  [`experiments/plain-with-prefix`](experiments/plain-with-prefix/REPORT.md) compare two ways of running the
  three failing-test tasks with "run commands plainly" (no `| tail`). **Without the shell prefix:** +33% tokens.
  Claude Code cut the failing output to 10K characters of passing tests, and Claude re-ran the commands.
  **With the prefix:** −9% tokens and −4% cost. That result decided the defaults: "plainly" is on for levels
  2 to 5, and only while the prefix is active.

Notes:
- The `py-git-history` prompt was clarified after an earlier round. "The last 40 commits" could mean the 40
  most recent commits or the last 40 that touched `src/`, and both arms got it wrong 2 times in 3. Both
  arms were re-run with the new prompt.
- Token totals add input, cache writes, cache reads and output across every API call in a session,
  including the small helper model Claude Code uses. Cost is Claude Code's own `total_cost_usd`.
- Reproduce: clone the repos listed in `bench/tasks.json` into one folder, then run
  `kompact prove --tasks bench/tasks.json --repos <folder> --reps 3`.
