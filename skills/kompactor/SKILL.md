---
name: kompactor
description: Kompactor token saver and code graph. Use when the user says /kompactor (start, stop, uninstall, status, a level name, review, audit, debt, graph), asks about token savings, or when you need to find code by topic, see who uses something, or check what a change affects.
---

Run these with Bash and report briefly. Kompactor token saver. `~/.kompactor/bin/kompactor` is created at session start; if it's missing, use `python3 "${CLAUDE_PLUGIN_ROOT}/kompactor/_launch.py"` instead.

/kompactor status (or just /kompactor): run `~/.kompactor/bin/kompactor status` and summarise it in a few lines.
Levels: `~/.kompactor/bin/kompactor presets`; change with `~/.kompactor/bin/kompactor config preset <N>` (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings; map words like "balanced" or "more savings").
/kompactor start: run `~/.kompactor/bin/kompactor start --no-browser` (turns Kompactor on: hooks, status line and the shell prefix that compacts failing commands, plus the dashboard on a free port), give the user the dashboard URL it prints, and if it says so, tell them to restart Claude Code.
/kompactor stop: `~/.kompactor/bin/kompactor stop` (pauses compaction, closes the dashboard). /kompactor uninstall: `~/.kompactor/bin/kompactor uninstall`, then relay any extra command it prints.
Savings: `~/.kompactor/bin/kompactor gain`.

Code graph (local, instant):
- `~/.kompactor/bin/kompactor graph query "words"` find code by topic; `~/.kompactor/bin/kompactor graph explain Name` one symbol, its users and tests
- `~/.kompactor/bin/kompactor graph callers Name` · `~/.kompactor/bin/kompactor graph impact <file|Name>` what a change affects and which tests to run
- `~/.kompactor/bin/kompactor graph report` overview · `~/.kompactor/bin/kompactor symbol Name` print a definition

/kompactor review: run `git diff HEAD`, then list concrete cuts, one line each (file:line, what to remove, why): code that duplicates an existing helper (check with graph query), options or abstractions nobody asked for, dead branches. Never cut validation, error handling, security or accessibility.
/kompactor audit: run `~/.kompactor/bin/kompactor graph unused` and `~/.kompactor/bin/kompactor graph report`; rank removals (likely dead first) with risks. Don't edit unless asked.
/kompactor debt: run `~/.kompactor/bin/kompactor debt` and summarize by severity.

Compacted output in full: `~/.kompactor/bin/kompactor show <id>`; search earlier outputs: `~/.kompactor/bin/kompactor search "text"`.
