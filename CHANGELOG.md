# Changelog

All notable changes to Kompactor. Versions follow [semantic versioning](https://semver.org/).

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
