---
name: kompactor
description: Kompactor token saver and code graph. Use when the user says /kompactor (setup, status, a level name, review, audit, debt, graph), asks about token savings, or when you need to find code by topic, see who uses something, or check what a change affects.
---

Run these with Bash and report briefly. Kompactor token saver.

/kompactor setup: run `kompactor setup --no-ui` (adds the status line and the shell prefix that compacts failing commands, which a plugin can't set itself), report what it printed, and tell the user to restart Claude Code.
Levels: `kompactor presets`; change with `kompactor config preset <N>` (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings; map words like "balanced" or "more savings").
Savings: `kompactor gain`. Dashboard: start `kompactor ui --no-browser` in the background and give the user the URL.

Code graph (local, instant):
- `kompactor graph query "words"` find code by topic; `kompactor graph explain Name` one symbol, its users and tests
- `kompactor graph callers Name` · `kompactor graph impact <file|Name>` what a change affects and which tests to run
- `kompactor graph report` overview · `kompactor symbol Name` print a definition

/kompactor review: run `git diff HEAD`, then list concrete cuts, one line each (file:line, what to remove, why): code that duplicates an existing helper (check with graph query), options or abstractions nobody asked for, dead branches. Never cut validation, error handling, security or accessibility.
/kompactor audit: run `kompactor graph unused` and `kompactor graph report`; rank removals (likely dead first) with risks. Don't edit unless asked.
/kompactor debt: run `kompactor debt` and summarize by severity.

Compacted output in full: `kompactor show <id>`; search earlier outputs: `kompactor search "text"`.
