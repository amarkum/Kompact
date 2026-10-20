---
name: kompact
description: Navigate code and logs cheaply. Use `kompact map` to orient in an unfamiliar repo, `kompact outline <file>` / `kompact symbol <Name>` instead of reading whole large files, `kompact show <id>` / `kompact search <q>` to get raw output that Kompact compacted, and `kompact gain` / `kompact estimate` when the user asks how many tokens are being saved.
---

# Kompact

Kompact's hooks already compact Bash output and outline big files on Read. Use these commands to spend fewer tokens on purpose (they're on PATH while the plugin is enabled):

| Need | Command | Instead of |
|---|---|---|
| Orient in a repo | `kompact map [dir] --budget 3000` | `ls -R`, reading many files |
| See a file's structure | `kompact outline path/to/file.ts` | Reading the whole file |
| Read one function/class | `kompact symbol Name` or `kompact symbol Class.method` | Reading the whole file |
| Full output a note says was trimmed | `kompact show <id> [--lines 100-160]` | Re-running the command |
| Find something in earlier outputs | `kompact search "TypeError"` | Re-running the command |
| Run a command with compaction outside the hook | `kompact run -- <cmd>` | |
| Bypass compaction once | prefix the command with `KOMPACT_RAW=1` | |

When the user asks about savings: `kompact gain` shows what the hooks saved live, and `kompact estimate` replays their past sessions and reports the % of tokens and cost Kompact would have saved.
