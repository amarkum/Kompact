# Kompact

**Cut the tokens Claude Code spends on noise, and see the % it saves.**

Most of a Claude Code session's tokens aren't your prompt or Claude's answer. They're tool output: `git log`, `npm install`, test runs, whole-file reads. That output is sent again on **every later turn** until the context is compacted. Kompact shrinks it before Claude sees it, keeping everything an agent needs (errors, failures, summaries, signatures).

```bash
kompact estimate   # replays YOUR past Claude Code sessions (~/.claude/projects) through Kompact
kompact gain       # what the hooks actually saved, live
```

`estimate` reports three numbers: the % of tool-output tokens removed, the % of total billed tokens saved, and the % of cost saved. Your savings depend on your work: build-, test- and git-heavy sessions save the most, and web research saves almost nothing.

## Measured on real commands

`python bench/bench.py <repo> [cmd…]` runs the commands and compares tokens before and after Kompact.

| Repo | Command | Before | After | Saved |
|---|---|---:|---:|---:|
| flask | `pytest -v tests` (1 failure, 482 passed) | 9,842 | 1,194 | **88%** |
| flask | `pytest tests` | 1,779 | 1,154 | 35% |
| flask | `git log -n 40` | 1,457 | 598 | 59% |
| flask | `git log --stat -n 15` | 1,000 | 370 | 63% |
| flask | `grep -rn 'def ' src` | 8,492 | 3,726 | 56% |
| flask | `find . -type f` | 2,901 | 1,465 | 50% |
| flask | `pip install -v -e .` | 797 | 557 | 30% |
| ky | `npm install` | 49,731 | 740 | **99%** |
| ky | `grep -rn await source` | 2,938 | 1,463 | 50% |
| ky | `git log -n 40` | 1,918 | 882 | 54% |

Outline-first reads (first `Read` of a big source file returns its skeleton with line ranges):

| File | Lines | Full read | Outline | Saved |
|---|---:|---:|---:|---:|
| flask `src/flask/app.py` | 1,625 | 14,084 | 1,490 | 89% |
| flask `src/flask/sansio/app.py` | 1,014 | 8,706 | 1,601 | 82% |
| ky `source/core/Ky.ts` | 1,376 | 12,452 | 919 | 93% |

The failing test's traceback, the `FAILED` line and the summary are all kept. Only passing-test lines, progress bars, download chatter and repeats are dropped.

## How it works: four layers, one install

| Layer | Hook | What it does | Inspired by |
|---|---|---|---|
| **Bash output compaction** | `PostToolUse(Bash)` → `updatedToolOutput` | Command-aware filters: git status/log/diff/push, test runners (pytest, jest, vitest, go, cargo…), package managers/builds, `find`/`ls -R`/`tree`, grep/rg. Then generic passes: ANSI and progress-bar stripping, repeat collapsing, long-line clipping, and head+tail truncation that **keeps error lines from the middle**. The raw output is stashed locally (`kompact show <id>`). | rtk, context-mode |
| **Outline-first reads** | `PreToolUse(Read)` | First full read of a source file over 400 lines is answered with its outline: classes, functions and methods with `[L120-184]` ranges. Claude then reads just the ranges it needs. **Calling Read again returns the whole file**, so it never blocks. | graphify, token-savior, aider repo-map, repomix `--compress` |
| **Read dedupe** | `PreToolUse(Read)` | Re-reading an unchanged file (same range) in the same session gets a one-line "still in your context" reply. Retry, edits and compaction all reset it. | token-optimizer |
| **Terse style** | `SessionStart` | Under 150 tokens of rules: no preamble or recaps, minimal code, use offsets and outlines. `lite` (default), `full` or `off`. | caveman, ponytail, claude-token-efficient |

Plus on-demand tools Claude (or you) can call: `kompact map` (dependency-ranked repo skeleton within a token budget), `kompact outline`, `kompact symbol Class.method`, `kompact search` (FTS5 over stashed outputs).

### Design choices (what we took, and what we avoided)

- **Post-processing, not command rewriting.** rtk rewrites your Bash commands via a `PreToolUse` hook. That can auto-approve commands, and it breaks `cd`/`export` state. Kompact uses `PostToolUse.updatedToolOutput`: your command runs exactly as written and the permission flow is untouched. Only what Claude *reads* changes.
- **No MCP server.** MCP tool schemas cost tokens on every turn. Kompact's on-demand tools are plain CLI commands (the plugin's `bin/` is on PATH), described in a small skill that loads only when relevant.
- **Never a dead end.** Every denial is "deny once, allow on retry". Every compaction leaves a `kompact show <id>` pointer to the raw output. Prefix a command with `KOMPACT_RAW=1` to skip compaction. Every hook fails open.
- **Honest numbers.** `kompact gain` reverses a claimed saving when Claude reads the full file anyway. `kompact estimate` replays real transcripts and weights each removed token by how many later API calls would have re-sent it (cache read 0.1×, cache write 1.25×, output 5×). Independent tests of popular tools found much less than advertised (Caveman ~8.5% vs 65% claimed, Ponytail ~10% vs ~20%), so measure, don't trust.
- **Zero dependencies.** Python ≥3.9 stdlib only (sqlite3 + FTS5). `pip install tiktoken` for exact token counts.

## Install

**As a Claude Code plugin** (hooks + skill + `kompact` on PATH):

```
/plugin marketplace add amarkum/Kompact
/plugin install kompact@kompact
```

**Or with pip**, then wire the hooks into `~/.claude/settings.json`:

```bash
pip install git+https://github.com/amarkum/Kompact
kompact install            # --project for .claude/settings.json; --uninstall to remove
kompact estimate           # what would it have saved on your past sessions?
```

## Commands

```
kompact estimate [--limit N] [--project DIR] [--style lite|full|off] [--json]
kompact gain                       live savings recorded by the hooks
kompact map [DIR] [--budget 4000]  ranked repo skeleton
kompact outline FILE…              symbols with line ranges
kompact symbol NAME [PATHS…]       source of a definition (Name or Class.method)
kompact show ID [--lines 10-80]    raw output that was compacted
kompact search QUERY               full-text search over stashed outputs
kompact run -- CMD                 run with compaction (for other agents / CI logs)
kompact filter --cmd "git log"     compact stdin
kompact config [KEY VALUE]         style, bash, bash_min_tokens, bash_max_lines,
                                   read_outline, read_outline_lines, read_dedupe
kompact doctor
```

Settings live in `~/.kompact/config.json` and can be overridden with `KOMPACT_<KEY>` environment variables.

## Landscape (October 2026)

| Tool | Layer | Approach | Independent result |
|---|---|---|---|
| [graphify](https://github.com/safishamsi/graphify) | context retrieval | tree-sitter knowledge graph of code + docs | 5–10× fewer tokens for codebase Q&A in one test; 71.5× headline is best-case |
| [ponytail](https://github.com/dtrick/ponytail) | output (code) | rules to write less code | ~10% per task (JetBrains test) |
| [caveman](https://github.com/JuliusBrussee/caveman) | output (prose) | terse-speech rules, 4 levels | −38% on one task; ~8.5% of output in another |
| [rtk](https://github.com/rtk-ai/rtk) | Bash output | Rust wrapper, rewrites commands | 60–90% on noisy output; ~0 on light tasks |
| [token-savior](https://github.com/Mibayy/token-savior) | file reads | MCP symbol lookup | −43% (best in one benchmark) |
| [claude-token-efficient](https://github.com/drona23/claude-token-efficient) | behavior | 11 CLAUDE.md rules | −40% |
| [context-mode](https://github.com/mksglu/context-mode) | tool output | stash big outputs in SQLite FTS5 | not benchmarked |
| [token-optimizer](https://github.com/alexgreensh/token-optimizer) | reads | delta re-reads, AST skeletons | −18% |
| [repomix](https://github.com/yamadashy/repomix) | packing | `--compress` to signatures | ~70% size reduction |
| [code-review-graph](https://github.com/tirth8205/code-review-graph) | retrieval | AST graph + blast radius | −5% small repo; up to 49× on a monorepo |

Each tool covers one layer. Kompact combines the layers that compound (tool output, reads, style) behind one install, with an estimator so you can check the savings yourself.

## Development

```bash
python -m unittest discover tests
python bench/bench.py /path/to/repo "git log -n 40" "pytest -v"
```

MIT licensed.
