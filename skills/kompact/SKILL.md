---
name: kompact
description: Kompact token saver and code graph. Use when the user says /kompact (status, a level name, review, audit, debt, graph), asks about token savings, or when you need to find code by topic, see who uses something, or check what a change affects.
---

Run these with Bash and report briefly. Kompact token saver.

Levels: `kompact presets`; change with `kompact config preset <N>` (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings; map words like "balanced" or "more savings").
Savings: `kompact gain`. Dashboard: start `kompact ui --no-browser` in the background and give the user the URL.

Code graph (local, instant):
- `kompact graph query "words"` find code by topic; `kompact graph explain Name` one symbol, its users and tests
- `kompact graph callers Name` · `kompact graph impact <file|Name>` what a change affects and which tests to run
- `kompact graph report` overview · `kompact symbol Name` print a definition

/kompact review: run `git diff HEAD`, then list concrete cuts, one line each (file:line, what to remove, why): code that duplicates an existing helper (check with graph query), options or abstractions nobody asked for, dead branches. Never cut validation, error handling, security or accessibility.
/kompact audit: run `kompact graph unused` and `kompact graph report`; rank removals (likely dead first) with risks. Don't edit unless asked.
/kompact debt: run `kompact debt` and summarize by severity.

Compacted output in full: `kompact show <id>`; search earlier outputs: `kompact search "text"`.
