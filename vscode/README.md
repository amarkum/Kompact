# Kompactor for VS Code

Cut the tokens **Claude Code** spends on noise: test runs, installs, git output and whole-file reads. Works with the Claude Code VS Code extension and the CLI, because both read the same `~/.claude/settings.json`.

- **One switch:** on first start, click **Enable**. Kompactor adds its hooks to Claude Code; a backup of your settings is kept.
- **Quality vs tokens:** pick a level from *Max quality* to *Max savings* (`Kompactor: Choose Quality vs Tokens Level`), or fine-tune every setting in the dashboard.
- **Sidebar:** the Kompactor icon in the activity bar shows tokens and dollars saved (at the API prices of the model each session ran on) this session, in this project, today and over 30 days, what each recent turn saved (or "nothing to trim"), and the biggest wins.
- **Status bar:** the Kompactor icon with this session's tokens and dollars saved. After every Claude reply, the turn's savings flash by (or show as a notification; see `kompactor.turnSummary`).
- **Dashboard:** `Kompactor: Open Dashboard` shows per-turn savings, a live before/after preview on Python, Go, React and TypeScript output, per-project levels, and language settings.
- **Failing runs too:** Claude Code cuts a failing command's output down to its first and last few thousand characters. Kompactor's shell prefix runs tests, builds and linters to completion and hands Claude the failures and summary, with the exit code unchanged.
- **Code graph:** functions, classes, imports and calls for Python, Go, TypeScript and React, indexed locally. Claude uses it to find code and check what a change affects, and you can browse it in the dashboard.

Measured in real Claude Code sessions: fewer tokens and lower cost at every level, with the same answers. The `evidence/` folder of the Kompactor repo has the full results.

**Installing:** `pipx install kompactor && kompactor start` adds this extension to VS Code and Cursor automatically, or install the `.vsix` from the repo's GitHub Releases. The dashboard's **Setup** page lists the install commands for your repo, and a committed `.kompactor.json` sets the level for everyone working in a project.

Requires Python 3.9+ (no packages needed). Nothing leaves your machine.

| Setting | Default | |
|---|---|---|
| `kompactor.turnSummary` | `statusBar` | How to announce each turn's savings: `statusBar`, `notification` or `off` |
| `kompactor.showStatusBar` | `true` | Running savings in the status bar |
| `kompactor.pythonPath` | auto | Python used to run Kompactor |
| `kompactor.pricePerMillionTokens` | `0` | Override the input-token price in USD per million tokens. `0` uses the API price of the model each session ran on |
