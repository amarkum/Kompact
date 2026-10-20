# Kompact for VS Code

Cut the tokens **Claude Code** spends on noise: test runs, installs, git output and whole-file reads. Works with the Claude Code VS Code extension and the CLI, because both read the same `~/.claude/settings.json`.

- **One switch:** on first start, click **Enable**. Kompact adds its hooks to Claude Code; a backup of your settings is kept.
- **Quality vs tokens:** pick a level from *Max quality* to *Max savings* (`Kompact: Choose Quality vs Tokens Level`), or fine-tune every setting in the dashboard.
- **See the savings:** the status bar shows tokens saved this session and how much smaller the context is. After every Claude reply, the turn's savings flash by (or show as a notification; see `kompact.turnSummary`).
- **Dashboard:** `Kompact: Open Dashboard` shows per-turn savings, a live before/after preview on Python, Go, React and TypeScript output, per-project levels, and language settings.

Requires Python 3.9+ (no packages needed). Nothing leaves your machine.

| Setting | Default | |
|---|---|---|
| `kompact.turnSummary` | `statusBar` | How to announce each turn's savings: `statusBar`, `notification` or `off` |
| `kompact.showStatusBar` | `true` | Running savings in the status bar |
| `kompact.pythonPath` | auto | Python used to run Kompact |
