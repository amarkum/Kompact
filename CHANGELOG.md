# Changelog

All notable changes to Kompactor. Versions follow [semantic versioning](https://semver.org/).

## 0.8.2

- VS Code and Cursor: a **Kompactor** icon in the activity bar opens a sidebar with tokens and estimated dollars saved this session, in this project, today and over 30 days, what every recent turn saved (or "nothing to trim"), and the biggest wins.
- The status bar shows the Kompactor icon with the session's tokens and dollars saved. The price is a setting: `kompactor.pricePerMillionTokens` (default $3 per million input tokens).
- `kompactor start` adds the extension to VS Code and Cursor when they're installed (`--no-editor` skips it); the extension ships inside the PyPI package, so nothing is downloaded.
- `kompactor uninstall` also removes the extension and deletes `~/.kompactor`; `--keep-data` keeps it.
- `kompactor gain --json` reports tokens and dollars per session, project, day and 30 days, with recent turns.

## 0.8.1

- Dashboard: the Rebuild button's refresh icon is drawn correctly.

## 0.8.0

- Three commands to remember: `kompactor start` turns Kompactor on (hooks, status line, shell prefix, the `kompactor` command on PATH, and the dashboard), `kompactor stop` pauses it, `kompactor uninstall` removes it. `setup` is folded into `start`; the old name still works.
- `/kompactor start` replaces `/kompactor setup` in Claude Code.

## 0.7.9

- `kompactor: command not found` after `pip install` is fixed on first run: `python3 -m kompactor setup` or `start` (or the plugin's first session) links the command into a writable folder already on PATH, such as `~/.local/bin`. `kompactor uninstall` removes the link.

## 0.7.8

- README rewritten as a full reference: features, usage, every setting and environment variable, evidence, supported languages, FAQ and development guide.
- New dashboard screenshots, all in the light theme.
- Dashboard: the team panel points to PyPI and GitHub Releases.
- Added CONTRIBUTING.md and this changelog.

## 0.7.7

- The Claude Code plugin installs as `amarkum@kompactor`.

## 0.7.5

- The plugin manifest names its homepage, documentation, support and privacy links.

## 0.7.4

- The Stop hook no longer reads session transcripts: the context size comes from what Claude Code gives the status line.
- README documents everything Kompactor runs, reads and writes; added SECURITY.md and a privacy policy.
- The self-test hands hooks only the environment variables they need.

## 0.7.3

- The dashboard's install commands name the public repo, or a fork via `KOMPACTOR_REPO`.
- Installers only install the clone they run from; PyPI covers installs without a clone.

## 0.7.2

- Plain `kompactor` (and `/kompactor`) shows status, how it works, how to turn it off and where the evidence is.
- Published on PyPI: `pipx install kompactor`.
- Fixed missing graph context in outlines when paths go through a symlink.

## 0.7.1

- The plugin ships no `bin/` folder; hooks call `kompactor/_launch.py` directly.

## 0.5.0

- `kompactor start`, `stop` and `uninstall`; the dashboard runs in the background on a free port.

## 0.4

- Renamed from Kompact to Kompactor.
- Compaction of failing and oversized command output through the shell prefix.
- Code graph for Python, Go, TypeScript and React; quality-vs-tokens levels; per-turn savings; VS Code extension; A/B evidence with `kompactor prove`.
