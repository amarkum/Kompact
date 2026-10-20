<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/kompact-logo-dark.png">
    <img src="docs/brand/kompact-logo-light.png" alt="Kompact" width="240">
  </picture>
</p>

<p align="center"><b>Cut the tokens Claude Code spends on noise.</b><br>
Choose quality vs tokens on a dashboard, and see what every turn saved.</p>

<p align="center">Claude Code CLI and VS Code · Python, Go, TypeScript, React · Python standard library only · MIT</p>

---

Most of a Claude Code session's tokens aren't your prompt or Claude's answer. They're tool output: test runs, installs, `git log`, whole-file reads. That output is sent again on every later turn until the context is compacted. Kompact shrinks it before Claude reads it. It keeps every error, failing test, your own stack frames and the summary lines. It also gives Claude a local code graph and short rules for terser replies and smaller diffs.

**Measured in real Claude Code sessions** on Flask, Cobra, SWR, ky and zustand, at the default level:
**−11% tokens, −8% cost, −15% output tokens, same answers (27/27 correct with and without).** At Max savings: −15% tokens, −11% cost, still 27/27.
Failing test runs saved the most: **−33% tokens** on a Go test failure and **−37% cost** on a vitest failure.
[Full results](#evidence)

![Kompact dashboard: savings per turn](docs/dashboard-overview.png)

## Install

Pick one. All three give the same result, and everything is configurable later from the dashboard.

**VS Code.** Install [`dist/kompact-0.3.0.vsix`](dist/kompact-0.3.0.vsix) (Extensions › `⋯` › *Install from VSIX…*) and click **Enable** when Kompact asks. The status bar starts showing savings.

**Terminal** (macOS, Linux; needs Python 3.9+ and nothing else):
```bash
git clone https://github.com/amarkum/Kompact && ./Kompact/install.sh
```
Windows: `.\Kompact\install.ps1`. Once the repo is public, `curl -fsSL https://raw.githubusercontent.com/amarkum/Kompact/main/install.sh | sh` works too.

**Claude Code plugin:**
```
/plugin marketplace add amarkum/Kompact
/plugin install kompact@kompact
```
Then run `kompact setup` once, or click **Finish setup** in the dashboard. Plugins can't set a status line or Claude Code's shell prefix themselves.

The CLI and the VS Code extension read the same `~/.claude/settings.json`, so one install covers both. Setup adds Kompact's hooks, a status line (only if you don't have one) and the `/kompact` skill. On macOS and Linux it also sets `CLAUDE_CODE_SHELL_PREFIX`, which is how failing commands get compacted. It never replaces a status line or shell prefix you already have, and it keeps a backup in `settings.json.kompact-backup`. `kompact install --uninstall` removes all of it.

## What it does

| When | Kompact | How |
|---|---|---|
| Claude runs a command | Drops passing tests, progress bars, download chatter, library stack frames and lock-file diffs. Keeps errors, failures, your frames and summaries. The raw output is stashed (`kompact show <id>`). | `PostToolUse` hook |
| A command **fails** | Claude Code skips output hooks when a command exits non-zero, and cuts the output to its first and last ~5K characters, usually losing the failures at the end. Kompact's shell prefix runs tests, builds, linters and installs to completion, compacts them, and passes the exit code through. Your permission rules still apply to Claude's original command. | `CLAUDE_CODE_SHELL_PREFIX` |
| A command prints over ~30K chars | Claude Code saves it to a file and shows Claude a 2 KB preview. Kompact compacts the whole saved output instead. | `PostToolUse` hook |
| Claude opens a big source file | Returns its outline first: symbols with line ranges, signatures, who imports it and which tests cover it. Claude then reads only what it needs, and repeating the read returns the whole file. Unchanged re-reads get a one-line note. | `PreToolUse` hook |
| Claude first searches or reads code | A budgeted map of the most depended-on modules, given once (sessions that only run commands don't pay for it). | `PostToolUse` context |
| Anytime | A local code graph for Python, Go, TypeScript, JavaScript and React: find code by topic, callers, impact of a change with the tests to run, import cycles, dead code. | `kompact graph …`, dashboard |
| Every reply, subagents too | Two dials. Prose: answer first, no preamble or recap. Code: change nothing if possible, reuse before writing, smallest diff, one focused test, never cut validation or security. 0 to 177 tokens of rules, depending on level. | `SessionStart`, `SubagentStart` |
| After each turn | What the turn saved, in the reply, the CLI status line, the VS Code status bar and the dashboard. | `Stop` hook |

Kompact never changes what a command does. It can't strand Claude: every trimmed output has a raw copy, and every blocked read is "deny once, allow on retry". Every hook fails open.

## Quality vs tokens

![Quality vs tokens with a live preview](docs/dashboard-quality.png)

One level sets every option. Every option can also be changed on its own, globally or per project, on the dashboard. There's no config file to edit.

| Level | What Claude gets | Rules injected |
|---|---|---:|
| 1 Max quality | Almost everything. Only outputs over ~1.5k tokens are touched, and only pure noise is removed. Failing commands are compacted too, gently. | 0 |
| 2 Quality | Noisy commands compacted, passing tests hidden, one-line `git log`, outlines for files over 800 lines. Answer-first replies. | 72 |
| 3 **Balanced** (default) | Outlines from 400 lines, library frames trimmed, a 500-token code map, lean-code rules. | 156 |
| 4 Savings | Tighter caps, 3 lines of diff context, outlines from 250 lines, test-runner banners dropped, shorter prose. | 176 |
| 5 Max savings | 80-line caps, 1 line of diff context, outlines from 150 lines, telegraphic prose. | 177 |

Change the level from the dashboard (`kompact ui`, or **Kompact: Open Dashboard** in VS Code), the VS Code status bar, or in Claude Code chat (`/kompact max savings`, `/kompact balanced`). A repo can have its own level under **Projects & languages**.

## See the savings, per turn

| Where | What you see |
|---|---|
| Claude Code, after each reply | `Kompact: −8.2k tokens this turn (13.1k › 4.9k, −63%) · session −41k · context ≈31% smaller` |
| CLI status line | `Kompact −41.3k · ctx −31% · last turn −8.2k · Balanced` |
| VS Code status bar | Running savings. Each turn flashes its saving, and hovering shows details. |
| Dashboard | Per-turn chart, biggest wins, savings by feature and by project. |
| `kompact estimate` | Replays your past sessions through the current settings: the share of tool output, billed tokens and cost Kompact would have saved. |

The numbers are conservative. Savings count only what Claude would really have read. When Claude Code would have truncated an output anyway, only the truncated size counts. When Claude reads a whole file after its outline, the outline's saving is reversed.

## Code graph

![Code graph: module map and a query](docs/dashboard-graph.png)

`kompact graph build` indexes a repo in about a second (Flask: 85 files in 0.33 s). It runs in the background at session start and after edits. Nothing is sent anywhere and nothing is written to the repo.

```
kompact graph query "session cookie"     find code by topic, with line ranges and who uses it
kompact graph impact createStore         files that use it, files that only import its module, tests to run
kompact graph explain Name               one symbol: signature, callers, callees, tests
kompact graph callers / deps / path      who calls it, what it imports, how two modules connect
kompact graph report                     core modules, entry points, import cycles, tests by module
kompact graph unused                     dead-code candidates (exported-but-unused listed separately)
```

`/kompact review`, `/kompact audit` and `/kompact debt` in chat use the graph to find duplicated helpers, dead code and shortcuts.

## How it compares

Kompact borrows the best idea from each of these tools: graphify's code graph, ponytail's lean-code ladder, caveman's terse prose, rtk's command filters, context-mode's raw-output stash, and the symbol-level reads of token-savior and code-review-graph. It then fixes the gaps that independent tests found. Researched in October 2026 from each project's repo and the independent tests linked below.

**Features** (Yes, Partly, or —):

| | Kompact | [graphify](https://github.com/Graphify-Labs/graphify) | [ponytail](https://github.com/DietrichGebert/ponytail) | [caveman](https://github.com/JuliusBrussee/caveman) | [rtk](https://github.com/rtk-ai/rtk) | [token-savior](https://github.com/Mibayy/token-savior) | [context-mode](https://github.com/mksglu/context-mode) | [code-review-graph](https://github.com/tirth8205/code-review-graph) |
|---|---|---|---|---|---|---|---|---|
| Compacts command output | **Yes**, incl. failing runs | — | — | Partly (v4 proxy) | Yes, 100+ commands | Partly (opt-in) | Yes (sandbox) | — |
| Outline / symbol-level reads | **Yes**, automatic | Partly (strict mode) | Partly | Partly | Partly (`rtk read`) | Yes (MCP) | — | Yes (MCP) |
| Code graph and change impact | **Yes** (Py, Go, TS, React) | Yes, plus docs and images via an LLM | — | — | — | Yes | — | Yes |
| Terse-prose rules | **Yes**, 4 levels | — | Partly | Yes | — | — | — | — |
| Lean-code rules | **Yes** | — | Yes | Partly | — | Partly | — | — |
| Quality vs tokens control | **Yes**: 5 levels, every option, per project | Flags and env vars | 3 levels | Levels | TOML | Profiles | — | Partly |
| Per-turn savings shown | **Yes**: reply, status line, VS Code, dashboard | — | Partly (not in VS Code) | — | On demand (`rtk gain`) | — | Yes | Partly |
| Settings dashboard | **Yes** | Graph export | Yes | Partly | Partly | Yes | Hosted | Partly |
| VS Code | **Yes**, with its own extension | Yes | Partly | Yes | Yes | Partly | Yes | Yes |
| Real A/B evidence in the repo | **Yes**, with cost and correctness | Corpus ÷ answer ratio | Yes | Yes | — | Withdrawn, then partial | — | Upper bound |
| Dependencies | **None** (Python 3.9+ stdlib) | Python 3.10+, LLM for docs | Node | npm CLI, telemetry on by default | Rust binary | pip, MCP | MCP server (ELv2) | pip, tree-sitter |

**What happened when others measured them:**

| Tool | Activation in practice | Its own instructions | Independent result |
|---|---|---|---|
| **Kompact** | Hooks act on every tool call, so Claude doesn't have to choose to use them | 0–177 tokens of rules + a 63-token skill entry | −11% tokens, −8% cost, 27/27 correct ([evidence](#evidence); self-run, reproducible with `kompact prove`) |
| graphify | Nudges Claude to query the graph. An 87-session analysis found 4% of nudges followed; the nudges cost about 651k tokens against 176k from graphify's own answers ([#3435](https://github.com/Graphify-Labs/graphify/issues/3435)) | ~11k-token skill | 7.3× on code-only questions in one test. The 71.5× headline divided the whole corpus by one answer and has been dropped from its README |
| ponytail | Hooks inject its rules. As a plain skill it activated in 0 of 10 runs | Rules + a codebase map at each start | Cost −10.3%, code −15%, quality unchanged ([JetBrains](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/), ~80 tasks) |
| caveman | Hooks inject its rules | ~1,160 tokens | Output −8.5%, cost ≈ −10% per task ([JetBrains](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)) |
| rtk | A hook rewrites commands; the rewrites bypass permission rules (rtk #4644) | None | Cost +7.6% at low effort, ±0% at high ([JetBrains](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/), 86 tasks). `rtk gain` counts all raw output, and reported 96.2M tokens saved while the bill rose |
| token-savior | Only when Claude calls its MCP tools: 1 of 143 sessions in a re-measurement it later withdrew | ~1.5k tokens of tool schemas (15 tools) and up | −43% tokens, −13% cost in one run ([computingforgeeks](https://computingforgeeks.com/reduce-claude-code-token-usage-tools/)) |
| context-mode | Hooks route big outputs into its sandbox; retrieval is via MCP | 11 tool schemas | No independent measurement found |
| code-review-graph | Only when Claude calls its MCP tools | 30 tool schemas | −5% in one run ([computingforgeeks](https://computingforgeeks.com/reduce-claude-code-token-usage-tools/)) |

**Where Kompact is better**
- **It works without being asked.** Graph tools and MCP servers save nothing when Claude doesn't call them, and the data above shows how often that happens. Kompact's savings come from hooks on every tool call. In the A/B runs, Claude never had to run a Kompact command for them to apply.
- **It handles the failing run.** That's where the noisiest output is, and where Claude Code itself drops the useful part. rtk handles failures too, but by rewriting commands, which bypasses your permission rules. Kompact acts after the permission check, on Claude's original command, with the exit code unchanged.
- **Its own instructions are small.** 156 tokens at the default level, against ~1,160 for caveman and an ~11k-token skill for graphify. The code map only appears once Claude starts exploring code.
- **Its savings numbers are honest.** It counts what Claude would actually have read, not raw output size, and it reverses a saving when Claude reads the full file anyway.
- **It's proven on cost and correctness, not just token counts.** `kompact prove` reruns the same tasks with and without Kompact in real Claude Code sessions, and the results are in this repo.
- **One control covers every layer**, from a dashboard, with a live preview of exactly what Claude would see.

**Where others are stronger**
- graphify builds a multimodal graph: docs, PDFs and images through an LLM, about 40 languages, Obsidian and Neo4j exports. Kompact's graph covers Python, Go, TypeScript, JavaScript and React code only.
- rtk has native filters for 100+ commands at under 10 ms each. Kompact's filters cover the common dev commands and run in Python (50–100 ms per hook).
- context-mode runs code in a sandbox and indexes huge outputs such as Playwright snapshots. token-savior keeps memory across sessions. Kompact does neither.

## Evidence

`kompact prove` runs each task in real headless Claude Code sessions (`claude -p`). Each task runs 3 times without Kompact and 3 times with it, interleaved, with the same prompt, tools, turn limit and budget cap. Kompact runs as an installed plugin at the default level. Tokens are input + cache writes + cache reads + output across every API call, and cost is Claude Code's own figure.

| Task | Repo | Tokens | Cost | Turns | Correct (without › with) |
|---|---|---:|---:|---|---|
| Find the failing Go test and its error | Cobra | **−33%** | **−20%** | 3.3 › 2.0 | 3/3 › 3/3 |
| Find where the session cookie is signed | Flask | **−26%** | −10% | 3.7 › 2.7 | 3/3 › 3/3 |
| Find the flag-group validation function | Cobra | −11% | −1% | 2.7 › 2.7 | 3/3 › 3/3 |
| Find how requests are deduplicated | SWR | −9% | +1% | 3.0 › 3.0 | 3/3 › 3/3 |
| Find the failing vitest test (`--reporter=verbose`) | zustand | −7% | **−37%** | 2.0 › 2.0 | 3/3 › 3/3 |
| Type-check and list errors | ky | +1% | −2% | 2.0 › 2.0 | 3/3 › 3/3 |
| Find the failing pytest tests | Flask | +1% | +2% | 2.0 › 2.0 | 3/3 › 3/3 |
| What does changing `createStore` affect | zustand | +1% | 0% | 2.0 › 2.0 | 3/3 › 3/3 |
| Most-changed files in the last 40 commits | Flask | +2% | +11% | 3.7 › 3.7 | 3/3 › 3/3 |
| **Total (54 sessions)** | | **−11%** | **−8%** | | **27/27 › 27/27** |

**The quality-vs-tokens control works in real sessions.** The same 27 Kompact sessions were re-run at each end of the range, against the same baseline:

| Level | Tokens | Cost | Output tokens | Correct |
|---|---:|---:|---:|---|
| 1 Max quality | −4% | −6% | −6% | 27/27 |
| 3 Balanced (default) | −11% | −8% | −15% | 27/27 |
| 5 Max savings | **−15%** | **−11%** | **−25%** | 27/27 |

What the numbers show:
- **The wins come from avoided turns.** Every turn re-sends the whole context. The vitest failure was 32K characters of passing tests; Kompact handed Claude 1K characters with the failure, at 37% lower cost. On the Go failure, Claude got the answer in one run instead of piping through `tail` and `grep` three or four times.
- **Short sessions pay a small fixed cost.** On 2-turn tasks whose output was already small, Kompact's rules and skill entry add about 1%. The git-history task varied with Claude's own approach in both arms.
- **One experiment shaped the defaults.** Telling Claude not to pipe output through `tail` cost **+33%** tokens before the shell prefix existed: Claude Code truncated the failing output and Claude re-ran the commands. With the prefix, the same rule gives **−9%**. So that rule is only on while the prefix is active ([experiments](evidence/README.md)).

Full report: [evidence/REPORT.md](evidence/REPORT.md). Every session's tokens, tool calls and answers: [evidence/results.json](evidence/results.json).

### Command output, measured directly

Tokens Claude receives for single commands on real repos (`bench/bench.py`):

| Repo | Command | Raw | Balanced | Max savings |
|---|---|---:|---:|---:|
| Flask | `pytest -v tests` (1 failure, 482 passed) | 9,842 | 1,138 (**−88%**) | 696 (**−93%**) |
| Flask | `grep -rn 'def ' src` | 8,492 | 3,230 (−62%) | 1,323 (−84%) |
| Flask | `git log -n 40` | 1,457 | 598 (−59%) | 598 (−59%) |
| ky | `npm install` (fresh) | ~33,000 | 469 (**−99%**) | 451 (−99%) |
| ky | `grep -rn await source` | 2,938 | 1,653 (−44%) | 1,058 (−64%) |
| Flask | Read `src/flask/app.py` (1,625 lines) › outline | 14,084 | 1,490 (−89%) | 1,490 (−89%) |
| ky | Read `source/core/Ky.ts` (1,376 lines) › outline | 12,452 | 919 (−93%) | 919 (−93%) |

## Languages

Kompact detects each repo's languages (`pyproject.toml` › Python, `go.mod` › Go, `tsconfig.json`/`package.json` › TypeScript, a `react` or `next` dependency › React). You can also pin them in the dashboard.

| | Python | Go | TypeScript / React |
|---|---|---|---|
| Library stack frames collapsed | `site-packages`, stdlib, `.venv` | `GOROOT`, `runtime/`, `pkg/mod` | `node_modules`, `node:internal`, `react-dom`, `next/dist` |
| Generated files (outline instead of a full read) | `*_pb2.py`, migrations | `*.pb.go`, `*_gen.go`, `zz_generated*`, mocks | `*.d.ts`, `*.min.js`, `dist/`, `.next/` |
| Lock files collapsed in diffs | `poetry.lock`, `uv.lock`, `Pipfile.lock` | `go.sum` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| Test runners | pytest, unittest, tox, nox | `go test`, gotestsum | jest, vitest, mocha, playwright |
| Code graph | `ast`: classes, functions, decorators, imports, calls | packages, structs, interfaces, methods | components, hooks, JSX renders, `tsconfig` paths, workspace packages |

## Commands

```
kompact setup                   enable for Claude Code (CLI + VS Code) and open the dashboard
kompact ui                      the dashboard
kompact presets                 list levels        kompact config preset 4    change level
kompact gain                    savings so far     kompact estimate           replay past sessions
kompact graph <action>          query, impact, explain, callers, deps, path, report, unused
kompact show ID / search TEXT   raw outputs Kompact compacted
kompact prove                   A/B test Kompact in real Claude Code sessions
kompact doctor                  check the installation (the dashboard's self-test runs every hook)
kompact install --uninstall     remove hooks, status line and shell prefix
```

The [usage guide](docs/usage.html) covers setup, levels, the graph, troubleshooting and FAQs. It's also built into the dashboard as **Guide**.

## Development

```bash
python -m unittest discover tests     # 73 tests, including the real shell prefix run as Claude Code runs it
node vscode/test/smoke.js             # VS Code extension against a mock API
./scripts/build-vsix.sh               # › dist/kompact-<version>.vsix
python -m kompact prove --tasks bench/tasks.json --repos <folder with the bench repos> --reps 3
```

How Claude Code's hooks behave on success, failure and very long output, and why Kompact uses a shell prefix rather than rewriting commands, is written up in [docs/SPEC.md](docs/SPEC.md).

MIT licensed.
