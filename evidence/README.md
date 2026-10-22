# Evidence

The A/B numbers here come from real headless Claude Code sessions (`claude -p`) on public repos, run with
`kompactor prove`. Each task runs three times without Kompactor and three times with it, using the same prompt,
tools, turn limit and budget cap. The two arms run interleaved, so model drift affects both equally.

- [`REPORT.md`](REPORT.md) is the main result: 9 tasks, 54 sessions, Kompactor at level 3 (Balanced),
  installed as a plugin (hooks and the `/kompactor` skill) with the shell prefix on, as `kompactor setup` leaves it.
  [`results.json`](results.json) has every session: tokens by type, cost, turns, the answer, each tool
  call with its result size, and Kompactor's own ledger.
- [`sessions`](sessions/REPORT.md) measures cost by session length: the same tasks on cobra, Flask, click and zustand, from one command (about 2 turns) to twenty steps (about 27 turns), without Kompactor, at each level, and with each technique by itself, 2 runs each. Its summary is what the Configuration page shows. Made with `bench/sessions.py`.
- [`real-repos`](real-repos/REPORT.md) measures compaction itself, without Claude sessions: real test suites, builds, `git log`/`git diff` and `grep` in 6 repositories (Python, TypeScript, C, Swift, Java), 22 outputs, with one planted failure per failing run. Median −61% per output at Balanced; every planted failure line reached Claude at levels 1, 3 and 5. Two of the repositories are private and reported by numbers only. Made with `bench/real_repos.py`.
- [`EXAMPLE.md`](EXAMPLE.md) shows, side by side, what Claude received for the same failing vitest run
  without Kompactor (15,617 characters, mostly passing tests) and with it (1,039 characters, exit code kept).
- [`levels/level-1`](levels/level-1/REPORT.md) and [`levels/level-5`](levels/level-5/REPORT.md) re-run the same
  27 Kompactor sessions at Max quality and Max savings against the same baselines: +3% and −12% tokens,
  −1% and −10% cost, 27/27 correct at both ends (Balanced: −16% tokens, −10% cost).
- [`experiments/plain-without-prefix`](experiments/plain-without-prefix/REPORT.md) and
  [`experiments/plain-with-prefix`](experiments/plain-with-prefix/REPORT.md) compare two ways of running the
  three failing-test tasks with "run commands plainly" (no `| tail`). **Without the shell prefix:** +33% tokens.
  Claude Code cut the failing output to 10K characters of passing tests, and Claude re-ran the commands.
  **With the prefix:** −9% tokens and −4% cost. That result decided the defaults: "plainly" is on for levels
  2 to 5, and only while the prefix is active.

Notes:
- An earlier Max-savings round got 2 of 27 answers wrong on the git-history task. In one, the 80-line cap cut
  a `git log --format=… --name-only` list that Claude had asked for. Output Claude shapes itself (a pipe or a
  format flag) is now kept verbatim, and the round was re-run.
- The two experiments under `experiments/` were recorded before the rename, when the tool was called Kompact.
- The `py-git-history` prompt was clarified after an earlier round. "The last 40 commits" could mean the 40
  most recent commits or the last 40 that touched `src/`, and both arms got it wrong 2 times in 3. Both
  arms were re-run with the new prompt.
- Token totals add input, cache writes, cache reads and output across every API call in a session,
  including the small helper model Claude Code uses. Cost is Claude Code's own `total_cost_usd`.
- Reproduce: clone the repos listed in `bench/tasks.json` into one folder, then run
  `kompactor prove --tasks bench/tasks.json --repos <folder> --reps 3`.
