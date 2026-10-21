# Kompactor privacy policy

Kompactor runs entirely on your own machine. It has no server and sends nothing to its authors or to any third party.

**What it stores, locally only.** To compact tool output and show savings, Kompactor keeps a copy of raw command output, savings figures and its settings in `~/.kompactor` (or `$KOMPACTOR_HOME`). That output can contain whatever your commands printed, including names or email addresses. It never leaves your machine.

**What it changes.** It adds hooks, a status line, a shell prefix and a skill to your Claude Code settings (`~/.claude`), and keeps a backup of the previous file.

**Network.** The dashboard listens only on `127.0.0.1`. Kompactor makes no outbound network requests of its own. The optional `kompactor prove` benchmark runs the Claude Code CLI, which talks to Anthropic as it always does.

**Deleting your data.** `kompactor uninstall --purge` removes Kompactor from Claude Code and deletes `~/.kompactor`.

Questions: open an issue at https://github.com/amarkum/kompactor/issues.
