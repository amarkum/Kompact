# Kompactor privacy policy

_Last updated: 21 October 2026_

Kompactor runs entirely on your own machine. It has no server, no accounts and no telemetry, and it sends nothing to its authors or to any third party.

**What it reads.** The tool output Claude Code passes to Kompactor's hooks, the files Claude reads (to outline them), your project's source code (to build the local code graph), and the context size Claude Code gives the status line. Kompactor's hooks never read your Claude Code session transcripts. `kompactor estimate` and the dashboard's **Replay your history** panel read your local session logs in `~/.claude/projects` only when you run them, to show what Kompactor would have saved; the result isn't stored or sent anywhere.

**What it stores, locally only.** Raw copies of the output it shortened (so Claude can fetch them with `kompactor show`), savings figures, the code graph index and its settings, in `~/.kompactor` (or `$KOMPACTOR_HOME`). That output can contain whatever your commands printed, including names or email addresses. History is deleted after 30 days by default; change this with the `retention_days` setting. Nothing is written to your repositories.

**What it changes.** `kompactor start` adds hooks, a status line (only if you have none), a shell prefix (only if none is set) and a `/kompactor` skill to your Claude Code configuration in `~/.claude`, and keeps a backup of the previous settings file.

**Network.** The dashboard listens only on `127.0.0.1`. Kompactor makes no outbound network requests of its own. If you install the optional `tiktoken` package for exact token counts, tiktoken downloads its token table once, on first use. The optional `kompactor prove` benchmark runs the Claude Code CLI, which talks to Anthropic as it always does.

**Deleting your data.** `kompactor uninstall --purge` removes Kompactor from Claude Code and deletes `~/.kompactor`. `kompactor stop` pauses it without deleting anything.

Questions: open an issue at https://github.com/amarkum/kompactor/issues. Security problems: see [SECURITY.md](SECURITY.md).
