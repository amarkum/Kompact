# Kompactor — product spec

Status: v0.4 · Last updated: 2026-10-20

## 1. Problem

In a Claude Code session most tokens are not the user's prompt or Claude's answer. They are tool output (test runs, installs, git, grep), whole-file reads, and the instructions every plugin adds. Each of those tokens is re-sent on every later turn until the context is compacted, and output tokens cost five times input tokens. Teams pay for this noise in money, rate limits and context space, and Claude gets slower and less focused as the context fills.

Existing tools each attack one layer and over-claim. Independent tests found ponytail −10% cost (claimed −26%), caveman −8.5% output (claimed −65%), rtk +7.6% cost at low effort, token-savior's tools called in 1 of 143 sessions, and graphify's "MANDATORY" prompts followed 4% of the time while costing more tokens than its answers.

## 2. Goals

1. Cut tokens across every layer that compounds (tool output, file reads, code navigation, reply length) without losing information Claude needs.
2. One control: a quality-vs-tokens level, with every individual setting available for those who want it.
3. Show the saving after every turn, in the CLI, in VS Code and in a dashboard, with numbers that survive an A/B test.
4. Setup in one step for the Claude Code CLI and the VS Code extension; no config files to edit.
5. First-class Python, Go, TypeScript and React support, detected per project.

### Non-goals

- Model routing or proxies that send traffic elsewhere. Kompactor is local; nothing leaves the machine.
- LLM-generated summaries of code or output (costly, non-deterministic, unverifiable).
- An MCP server. MCP tool schemas cost tokens on every turn and agents rarely call optional tools.
- Rewriting the user's commands (bypasses permission rules, breaks `cd`/`export`).

## 3. Principles

| Principle | Consequence |
|---|---|
| **Automatic beats optional.** | Savings come from hooks that act on every tool call. Commands Claude may call are a bonus, never the mechanism. |
| **Every injected token must pay for itself.** | Rules stay under ~200 tokens. No nagging prompts. The code map is budgeted and optional; outline context is one line. |
| **Never a dead end.** | Every trimmed output has a raw copy (`kompactor show <id>`). Every blocked read is "deny once, allow on retry". Every hook fails open. |
| **Keep what matters.** | Errors, failing tests, the user's own stack frames, summaries, diffs of real code and anything the user explicitly prints (`cat`) survive at every level. |
| **Measure honestly.** | Savings are reversed when Claude reads the full file anyway. Estimates weight tokens by how often they would be re-sent. Claims are backed by real `claude -p` A/B runs. |
| **Zero dependencies, fast.** | Python standard library only. Hooks run in ~50–80 ms. |

## 4. Users

- **Developer using Claude Code** in a terminal or VS Code on Python, Go, TypeScript or React repos. Wants lower cost and faster sessions without babysitting a tool.
- **Team lead** rolling it out to a team. Wants a one-file install (VS Code `.vsix` or a one-liner), sensible defaults, per-repo levels, and proof it works.

## 5. Feature layers

### 5.1 Command output (three paths, one filter set)
Command-aware filters for git, test runners (pytest, go test, jest, vitest, mocha, playwright), package managers and builds (pip, uv, poetry, npm, pnpm, yarn, go, cargo, vite, next, webpack, docker), listings and search. Generic passes: ANSI and progress removal (only with a real progress signal), exact-duplicate collapsing, number-only collapsing for build output and timestamped logs, line clipping, and head/tail truncation that keeps important lines from the middle. Language profiles trim library stack frames (site-packages, GOROOT/runtime, node_modules), collapse lock-file and generated-file diffs. The raw output is stashed locally and searchable.

Claude Code hands command output to Claude in three different ways, and each needs its own hook point (all verified against Claude Code 2.1 with real sessions):

| Command result | What Claude Code does | What Kompactor does |
|---|---|---|
| Succeeds, under ~30K chars | `PostToolUse` with the full output | Replaces it via `updatedToolOutput` |
| Succeeds, over ~30K chars | Saves it to a file, gives hooks only the first 30K chars, shows Claude a 2 KB preview | Reads the saved file, compacts the whole output, drops the file reference so Claude gets the compacted text instead of the preview (plain `cat`/`head` views keep the preview) |
| Fails (non-zero exit) | Skips `PostToolUse`. `PostToolUseFailure` can only add context. The error text is cut to its first and last ~5K chars, which usually loses the failures at the end of a test run | **Shell prefix.** `CLAUDE_CODE_SHELL_PREFIX` points at `~/.kompactor/bin/kompactor-shell`, which Claude Code runs as `kompactor-shell '<command>'`. Finite, noisy commands (tests, builds, linters, type checks, installs) run to completion, their output is compacted, and the exit code passes through unchanged. Everything else, and everything if Kompactor is missing, runs untouched. Permission rules still apply to Claude's original command, because the prefix only acts when the command runs |

Rewriting the command in `PreToolUse` was rejected after testing. Claude Code checks permissions against the rewritten command, so `pytest … | kompactor filter` breaks the user's allow rules. It also refuses braces, subshells and `${PIPESTATUS}`, which are the only ways to keep the exit code through a pipe.

### 5.2 File reads (PreToolUse · Read)
- **Outline first:** the first full read of a large source file returns its outline (symbols with line ranges, signatures, first docstring line) plus one graph line ("imported by …; tests: …"). Repeating the read returns the file.
- **Skip unchanged re-reads:** a repeat read of the same unchanged range gets a one-line note once.
- Partial reads (offset/limit) are never blocked. State resets on compaction.

### 5.3 Code graph
Incremental SQLite graph per project, outside the repo. Python via `ast`; Go and TS/JS/React via targeted parsers. Nodes: files/packages and symbols (functions, methods, classes, structs, interfaces, types, components, hooks, constants). Edges: imports (relative, aliased, `tsconfig` paths, workspace package names), calls, JSX renders, inheritance, decorators; type-only imports are marked.
- Queries: `query` (topic search over names, docstrings and file names, with usage and callees), `callers`, `deps`, `impact` (dependents and tests to run), `path`, `explain`, `report` (core modules, key files, most used symbols, entry points, import cycles, tests by module), `unused` (dead-code candidates).
- Used automatically: outline context, a budgeted code map the first time Claude searches or reads code (sessions that only run commands don't pay for it), refresh in the background at session start and after edits.

### 5.4 Reply style (SessionStart, and subagents)
Two independent dials:
- **Prose:** `off`, `lite` (answer first, no preamble or recap), `full` (short sentences, no narration between tool calls), `ultra` (telegraphic).
- **Code:** `normal`, `lean` (ponytail-style ladder: change nothing, reuse what exists, smallest diff; check callers/tests/config; one focused test; never cut validation, security, data-loss handling or accessibility), `strict` (also proposes the smaller alternative before building and marks shortcuts).
Never compressed: code, commands, paths, error text, numbers, negations, security warnings, commit messages and docs.
`/kompactor review` (diff bloat review), `/kompactor audit` (graph-backed dead code and over-engineering), `/kompactor debt` (shortcut/TODO ledger).

### 5.5 Measurement
- Per turn: `Stop` hook totals the turn (before › after, context smaller by …) and shows it in Claude Code, the CLI status line, the VS Code status bar and the dashboard.
- `kompactor estimate`: replays past transcripts through the current settings.
- `kompactor prove`: runs the same tasks with and without Kompactor through real `claude -p` sessions and reports tokens, cost, turns and answer correctness.

## 6. Settings

The preset sets every value, and any value can be overridden. From least to most specific:
your level and overrides (dashboard, applies everywhere) › the repo's committed `.kompactor.json` (the team's
level and settings for that repo) › your own choice for that project › `KOMPACTOR_<SETTING>` environment
variables. A broken or unknown entry in `.kompactor.json` is ignored.

| Setting | Type | 1 Max quality | 2 Quality | 3 Balanced | 4 Savings | 5 Max savings |
|---|---|---|---|---|---|---|
| Compact command output | bool | on | on | on | on | on |
| Compact failing commands too (shell prefix) | bool | on | on | on | on | on |
| Let Kompactor trim command output (only with the shell prefix) | bool | off | on | on | on | on |
| Leave outputs smaller than (tokens) | int | 1500 | 1000 | 300 | 150 | 80 |
| Max lines kept per output | int | 600 | 400 | 200 | 120 | 80 |
| Longest line kept (chars) | int | 2000 | 1000 | 500 | 300 | 200 |
| Search matches per file | int | 50 | 25 | 12 | 8 | 5 |
| Hide passing tests | bool | off | on | on | on | on |
| Drop test-runner headers | bool | off | off | off | on | on |
| Trim library stack frames | bool | off | off | on | on | on |
| Diff context lines (−1 = all) | int | all | all | all | 3 | 1 |
| One-line git log | bool | off | on | on | on | on |
| Never compact these commands | list | — | — | — | — | — |
| Outline-first file reads | bool | off | on | on | on | on |
| Outline files longer than (lines) | int | 1500 | 800 | 400 | 250 | 150 |
| Show usages in outlines | bool | off | on | on | on | on |
| Skip unchanged re-reads | bool | on | on | on | on | on |
| Code graph | bool | on | on | on | on | on |
| Code map on first search or read (tokens) | int | 0 | 0 | 500 | 700 | 900 |
| Prose style | choice | off | lite | lite | full | ultra |
| Code style | choice | normal | normal | lean | lean | lean |
| Apply rules to subagents | bool | on | on | on | on | on |

General (not part of presets): show savings after each turn, status line, data retention (days).

## 7. Surfaces

| Surface | What it offers |
|---|---|
| Dashboard (`kompactor ui`, VS Code webview) | Overview (per-turn chart, where savings come from, biggest wins), Quality (level, live preview with removed lines, grouped settings), Code graph (stats, map, interactive module graph, search), Projects & languages (with team levels from `.kompactor.json`), Setup (status, enable/disable, self-test, and "Share with your team" commands for the repo this copy came from), Guide |
| VS Code extension | One-click enable, status-bar savings, per-turn flash or notification, level picker, dashboard webview |
| Claude Code chat | `/kompactor`, `/kompactor setup`, `/kompactor <level>`, `/kompactor review`, `/kompactor audit`, `/kompactor debt`, `/kompactor graph <question>` |
| CLI | `setup`, `ui`, `presets`, `config`, `gain`, `estimate`, `prove`, `graph …`, `outline`, `symbol`, `show`, `search`, `doctor` |

## 8. Team use

Kompactor is meant to live in an organisation's private repo; nothing is published to a public registry.
- **Install paths:** the repo is a Claude Code plugin marketplace (`.claude-plugin/marketplace.json`), so
  teammates add it with `/plugin marketplace add <org>/<repo>` using their own git access. It can also be
  installed from a clone (`install.sh`, `install.ps1`) or as a VS Code extension file built from the repo
  (`scripts/build-vsix.sh`).
- **Rollout per project:** a committed `.claude/settings.json` can list the marketplace and enable the plugin,
  so Claude Code offers it to everyone who opens the project.
- **Team defaults:** a committed `.kompactor.json` sets the level and any setting for a repo (section 6).
- **Exact commands for your repo:** the dashboard and guide show install commands for the public repo,
  `amarkum/kompactor`, or for a team's fork when `KOMPACTOR_REPO` names it. Kompactor never reads git remotes
  or install records to work this out.
- **Name:** the tool was called Kompact. It was renamed because an unrelated PyPI package, `kompact`, installs a
  `kompact` command, which would have been called instead of this tool on machines that have both.
  Installing Kompactor replaces an old Kompact install's hooks, status line, shell prefix and skill, and
  never touches entries that belong to other tools.

## 9. Quality bar

- Data safety tests: grep hits with percentages, coverage tables, kubectl rows, git subjects and `cat` output survive every level; failing tests and user frames survive every level.
- Hooks: fail open, < 100 ms typical, no permission changes, idempotent install that never replaces a user's status line or shell prefix and keeps a settings backup. The shell prefix is written to user settings only (never a project's committed `.claude/settings.json`), costs nothing for commands it doesn't handle, and falls back to running the command untouched on any Kompactor problem.
- UI: works offline (bundled fonts), light and dark, phone width, keyboard focus, no console errors (Playwright check).
- Evidence: real Claude Code A/B runs on Python, Go and TypeScript repos committed under `evidence/`.

## 10. Competitive position

| | Kompactor | graphify | ponytail | caveman | rtk | token-savior | context-mode |
|---|---|---|---|---|---|---|---|
| Layers covered | output, reads, graph, prose, code | graph | code size | prose | shell output | reads, graph | tool output |
| Works without Claude choosing to call it | yes (hooks) | prompts (4% followed) | rules | rules | yes | MCP (rarely called) | yes |
| Cost of its own instructions | ~150 tokens | ~11k skill | rules + map | ~1,160 | 0 | 1.5–7k schemas | schemas |
| Measured with real A/B | yes (`evidence/`) | corpus ÷ answer ratio | yes | yes | no | partially | no |

## 11. Open questions

- Code map default: kept at 500 tokens for Balanced until A/B evidence across more repos says otherwise.
- `strict` code style is opt-in; it can push back on requests, which some users dislike.
