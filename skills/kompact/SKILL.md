---
name: kompact
description: Kompact token saver. Use when the user says /kompact, asks how many tokens Kompact saved, wants to change its quality vs tokens level, or open its dashboard. Also lists cheap code-navigation commands (map, outline, symbol) and how to see raw output Kompact compacted.
---

# Kompact

Kompact's hooks compact Bash output and outline big files on Read. Run these with Bash and report results briefly.

## User requests
- Show savings: `kompact gain`
- Quality vs tokens levels: `kompact presets`
- Change level (1 Max quality, 2 Quality, 3 Balanced, 4 Savings, 5 Max savings): `kompact config preset <N>`. Map words like "max savings", "balanced", "more quality" to the closest level.
- Open the dashboard: run `kompact ui --no-browser` in the background and give the user the printed URL.

## Spend fewer tokens yourself
| Need | Command |
|---|---|
| Orient in a repo | `kompact map [dir] --budget 3000` |
| A file's structure | `kompact outline path/to/file.ts` |
| One function or class | `kompact symbol Name` or `kompact symbol Class.method` |
| Full output that a note says was trimmed | `kompact show <id> [--lines 100-160]` |
| Find something in earlier outputs | `kompact search "TypeError"` |
| Bypass compaction once | prefix the command with `KOMPACT_RAW=1` |
