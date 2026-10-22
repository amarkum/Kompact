<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/amarkum/kompactor/main/docs/brand/kompactor-logo-dark.png">
    <img src="https://raw.githubusercontent.com/amarkum/kompactor/main/docs/brand/kompactor-logo-light.png" alt="Kompactor" width="240">
  </picture>
</p>

<p align="center"><b>Cut the tokens Claude Code spends on noise.</b><br>
Shorter tool output for Claude, the same answers, and a dashboard that shows what every turn saved.</p>

<p align="center">Claude Code CLI and VS Code · Python, Go, TypeScript, React · no dependencies (Python 3.9+) · MIT</p>

---

Most of a Claude Code session's tokens aren't your prompt or Claude's answer. They're tool output: test runs, installs, `git log`, whole-file reads. That output is sent again on every later turn until the context is compacted. Kompactor shrinks it before Claude reads it, and always keeps errors, failing tests, your own stack frames and summary lines.

**Measured in real Claude Code sessions:** −16% tokens, −10% cost, −22% output tokens at the default level, with the same answers (27/27 correct with and without). Up to −37% cost on a failing test run. [See the evidence](#evidence)

![Kompactor dashboard: savings per turn](https://raw.githubusercontent.com/amarkum/kompactor/main/docs/dashboard-overview.png)

## Contents

[Install](#install) · [After you install](#after-you-install) · [How it works](#how-it-works) · [Examples](#examples) · [Use it from Claude Code](#use-it-from-claude-code) · [Quality vs tokens](#quality-vs-tokens) · [See your savings](#see-your-savings) · [Turn it off](#turn-it-off-or-remove-it) · [What it runs and changes](#what-kompactor-runs-and-changes) · [Evidence](#evidence) · [Code graph](#code-graph) · [Teams](#use-it-across-a-team) · [Troubleshooting](#troubleshooting) · [Commands](#commands) · [Support](#support-and-security)

## Install

Pick one. All of them set up the same thing, and the CLI and the VS Code extension share it.

**Claude Code plugin** (recommended). In any Claude Code session, one line at a time:
```
/plugin marketplace add amarkum/kompactor
/plugin install amarkum@kompactor
/kompactor setup
```
The last step adds the status line and the shell prefix that compacts failing commands, which a plugin can't set itself. Then restart Claude Code.

**pip / pipx / uv** (macOS, Linux, Windows):
```bash
pipx install kompactor        # or: pip install kompactor · uv tool install kompactor
kompactor setup
```

**VS Code.** Download `kompactor-0.7.7.vsix` from [Releases](https://github.com/amarkum/kompactor/releases), install it (Extensions › `⋯` › *Install from VSIX…*), and click **Enable** when Kompactor asks.

## After you install

1. **Restart Claude Code** (CLI or VS Code). Kompactor starts with the next session.
2. **Work as usual.** You don't call Kompactor; it acts on Claude's tool calls by itself. After each reply you'll see a line such as `Kompactor: −8.2k tokens this turn`, and the status line shows the running total.
3. **Check it's on:** run `kompactor` in a terminal (or `/kompactor` in Claude Code). It shows whether it's on, your level, savings so far and how to change things:
   ```
   Kompactor 0.7.7: ON
     Connected via the Claude Code plugin. New Claude Code sessions are compacted.
     Level: Balanced (level 3 of 5). Change it: `kompactor config preset 1-5`, the dashboard, or /kompactor balanced
     Saved so far: 41.3k tokens (−38%) over 52 tool calls. Details: `kompactor gain`
   ```
4. **Open the dashboard:** `kompactor start` runs it in the background on a free port and prints the address.

## How it works

Kompactor uses Claude Code's hooks, so it sits between Claude's tools and Claude itself:

| When Claude… | Kompactor… |
|---|---|
| runs a command | drops passing tests, progress bars, download chatter, library stack frames and lock-file diffs. Keeps errors, failures, your frames and summaries. |
| runs a command that **fails** | runs it to completion through a shell prefix, compacts it and passes the exit code through. (Without this, Claude Code cuts failing output to its first and last ~5K characters, usually losing the failures at the end.) |
| opens a big source file | returns its outline first: symbols with line ranges, who imports it and which tests cover it. Claude reads only the ranges it needs; repeating the read returns the whole file. |
| first searches the code | gives a short map of the most depended-on modules, once per session. |
| writes a reply | gets a few lines of rules: answer first, smallest diff, reuse before writing (0–177 tokens, depending on the level). |

**Nothing is lost.** Every shortened output keeps a raw copy that Claude can fetch with `kompactor show <id>`. Kompactor never changes what a command does, your permission rules still apply, and if anything goes wrong it lets the original output through. Everything runs on your machine; nothing is sent anywhere ([privacy](https://github.com/amarkum/kompactor/blob/main/PRIVACY.md)).

## Examples

Ask Claude Code the way you normally would. These prompts come from the [evidence](#evidence) runs:

| You ask | What Kompactor does | Measured |
|---|---|---|
| "Run the tests and tell me which one fails and why." | Claude sees the failing test, its error and the summary line instead of hundreds of passing tests, even when the run exits non-zero. | Go: −33% tokens; vitest: −37% cost |
| "Where is the session cookie signed?" | Big files arrive as outlines with line ranges, and the first search adds a short map of the main modules, so Claude finds the code in fewer turns. | Flask: −26% tokens |
| "Install the dependencies and check that it builds." | Download and progress chatter is dropped; warnings, errors and the result are kept. | `npm install`: ~33,000 › 469 tokens |
| "What does changing `createStore` affect?" | The code graph lists the files that use it and the tests to run. | 27/27 answers correct |
| `/kompactor review` | Lists cuts in your current diff: duplicated helpers, unused options, dead branches. | |

## Use it from Claude Code

Type these in any Claude Code chat:

| Command | What it does |
|---|---|
| `/kompactor` or `/kompactor status` | Is it on, current level, savings so far |
| `/kompactor balanced`, `/kompactor max savings`, `/kompactor max quality` | Change the level |
| `/kompactor stop` · `/kompactor start` | Pause it · turn it back on |
| `/kompactor review` | Suggests cuts in your current diff: duplicated helpers, unused options, dead branches |
| `/kompactor audit` · `/kompactor debt` | Dead-code candidates · a list of FIXME/HACK/TODO shortcuts |

Claude also uses the code graph on its own when it needs to find code or check what a change affects.

## Quality vs tokens

![Quality vs tokens with a live preview](https://raw.githubusercontent.com/amarkum/kompactor/main/docs/dashboard-quality.png)

One level sets everything. Change it on the dashboard, with `/kompactor <level>` in chat, or with `kompactor config preset <1-5>`. Each project can have its own level.

| Level | What Claude gets |
|---|---|
| 1 Max quality | Almost everything. Only outputs over ~1.5k tokens are touched, and only pure noise is removed. |
| 2 Quality | Noisy commands compacted, passing tests hidden, one-line `git log`, outlines for files over 800 lines. |
| 3 **Balanced** (default) | Outlines from 400 lines, library frames trimmed, a 500-token code map, lean-code rules. |
| 4 Savings | Tighter caps, 3 lines of diff context, outlines from 250 lines, shorter prose. |
| 5 Max savings | 80-line caps, 1 line of diff context, outlines from 150 lines, telegraphic prose. |

The dashboard also lets you change any single option, with a live preview of exactly what Claude would see.

## See your savings

| Where | What you see |
|---|---|
| After each reply | `Kompactor: −8.2k tokens this turn (13.1k › 4.9k, −63%) · session −41k · context ≈31% smaller` |
| CLI status line | `Kompactor −41.3k · ctx −31% · last turn −8.2k · Balanced` |
| VS Code status bar | Running savings; hover for details |
| Dashboard (`kompactor start`) | Per-turn chart, biggest wins, savings by feature and by project |
| `kompactor gain` | The same numbers in the terminal |
| `kompactor estimate` | Replays your **past** sessions and shows what Kompactor would have saved |

The numbers are conservative: they count only what Claude would really have read, and a saving is reversed when Claude reads the full file anyway.

## Turn it off or remove it

```bash
kompactor stop        # pause: Claude Code output passes through untouched; settings are kept
kompactor start       # turn it back on
kompactor uninstall   # remove hooks, status line, shell prefix and skill (add --purge to delete ~/.kompactor too)
```
Then remove the package the way you installed it: `claude plugin uninstall amarkum@kompactor`, `pipx uninstall kompactor`, or uninstall the extension in VS Code. Setup never replaces a status line or shell prefix you already had, and keeps a backup in `~/.claude/settings.json.kompactor-backup`.

## What Kompactor runs and changes

Everything below happens on your machine. Kompactor makes no network requests of its own and has no telemetry. (If you install the optional `tiktoken` package for exact token counts, tiktoken downloads its token table once, on first use.)

**What it runs.** Python hooks that Claude Code calls (`python3 kompactor/_launch.py hook <name>` from the plugin folder): after Bash, Read, Grep, Glob and edit tool calls; before Read; at session start, subagent start and before compaction; and when a turn ends. After `/kompactor setup` on macOS and Linux, Claude's Bash commands run through Kompactor's shell prefix (`~/.kompactor/bin/kompactor-shell`) so failing runs can be compacted too. The prefix runs after Claude Code's permission check, on Claude's original command, and returns its exit code unchanged.

**What it adds to Claude's context.** Compacted tool output, outlines in place of large file reads, a code map once per session, a one-line savings note after each turn, and short reply rules at session start and for subagents. The rules are plain text you can read in [`kompactor/rules.py`](https://github.com/amarkum/kompactor/blob/main/kompactor/rules.py); the level decides which ones apply (none at level 1).

**What it reads.** The tool output Claude Code passes to its hooks, the files Claude reads (to outline them), your project's source (for the code graph), and the context size Claude Code gives the status line. Hooks never read your session transcripts. `kompactor estimate` and the dashboard's **Replay your history** panel read your local Claude Code session logs in `~/.claude/projects`, only when you run them, to show what Kompactor would have saved; the result isn't stored or sent anywhere.

**What it writes.** `~/.kompactor/`: settings, the savings ledger, raw copies of shortened output (for `kompactor show`), the code graph index and the `~/.kompactor/bin/` launchers (written at session start). History is deleted after 30 days by default (`retention_days`). Setup edits `~/.claude/settings.json` to add Kompactor's hooks (non-plugin installs), a status line (only if you have none) and `CLAUDE_CODE_SHELL_PREFIX` (only if it isn't set), keeping a backup in `settings.json.kompactor-backup`; non-plugin installs also get the `/kompactor` skill in `~/.claude/skills`. Nothing is written to your repositories.

**What it never does.** Change your permission rules or sandbox settings, change what a command does, or send your code or output anywhere. Details: [privacy policy](https://github.com/amarkum/kompactor/blob/main/PRIVACY.md).

## Evidence

`kompactor prove` runs each task in real headless Claude Code sessions (`claude -p`), 3 times without Kompactor and 3 times with it, interleaved, with the same prompt, tools, turn limit and budget cap. Tokens are input + cache writes + cache reads + output across every API call; cost is Claude Code's own figure.

| Task | Repo | Tokens | Cost | Turns | Correct (without › with) |
|---|---|---:|---:|---|---|
| Find the failing Go test and its error | Cobra | **−33%** | **−18%** | 3.3 › 2.0 | 3/3 › 3/3 |
| Find how requests are deduplicated | SWR | **−32%** | −12% | 3.0 › 2.0 | 3/3 › 3/3 |
| Find where the session cookie is signed | Flask | **−26%** | −11% | 3.7 › 2.7 | 3/3 › 3/3 |
| Find the flag-group validation function | Cobra | −24% | −6% | 2.7 › 2.3 | 3/3 › 3/3 |
| Most-changed files in the last 40 commits | Flask | −16% | +4% | 3.7 › 3.0 | 3/3 › 3/3 |
| Find the failing vitest test (`--reporter=verbose`) | zustand | −7% | **−37%** | 2.0 › 2.0 | 3/3 › 3/3 |
| Type-check and list errors | ky | +1% | −2% | 2.0 › 2.0 | 3/3 › 3/3 |
| Find the failing pytest tests | Flask | +1% | +3% | 2.0 › 2.0 | 3/3 › 3/3 |
| What does changing `createStore` affect | zustand | +17% | +4% | 2.0 › 2.3 | 3/3 › 3/3 |
| **Total (54 sessions)** | | **−16%** | **−10%** | | **27/27 › 27/27** |

At the other levels, against the same baseline:

| Level | Tokens | Cost | Output tokens | Correct |
|---|---:|---:|---:|---|
| 1 Max quality | +3% | −1% | 0% | 27/27 |
| 3 Balanced (default) | **−16%** | **−10%** | **−22%** | 27/27 |
| 5 Max savings | −12% | −10% | −22% | 27/27 |

- **The wins come from avoided turns.** Every turn re-sends the whole context. The vitest failure was 32K characters of passing tests; Kompactor gave Claude 1K characters with the failure, at 37% lower cost.
- **Short sessions pay a small fixed cost.** On 2-turn tasks with little output, Kompactor's rules add about 1%.
- **Single commands shrink much more** than whole sessions, because most of a session is Claude Code's own fixed context:

| Repo | Command | Raw tokens | Balanced | Max savings |
|---|---|---:|---:|---:|
| Flask | `pytest -v tests` (1 failure, 482 passed) | 9,842 | 1,138 (**−88%**) | 696 (**−93%**) |
| Flask | `grep -rn 'def ' src` | 8,492 | 3,230 (−62%) | 1,323 (−84%) |
| Flask | `git log -n 40` | 1,457 | 598 (−59%) | 598 (−59%) |
| ky | `npm install` (fresh) | ~33,000 | 469 (**−99%**) | 451 (−99%) |
| Flask | Read `src/flask/app.py` (1,625 lines) › outline | 14,084 | 1,490 (−89%) | 1,490 (−89%) |
| ky | Read `source/core/Ky.ts` (1,376 lines) › outline | 12,452 | 919 (−93%) | 919 (−93%) |

**Read more:** [full report](https://github.com/amarkum/kompactor/blob/main/evidence/REPORT.md) · [every session's tokens, tool calls and answers](https://github.com/amarkum/kompactor/blob/main/evidence/results.json) · [what Claude received in each arm for the same failing test run](https://github.com/amarkum/kompactor/blob/main/evidence/EXAMPLE.md) (15,617 vs 1,039 characters) · [how Kompactor compares with graphify, rtk, caveman and others](https://github.com/amarkum/kompactor/blob/main/docs/comparison.md)

**Check it on your own work:** `kompactor estimate` replays your past sessions, and `kompactor prove` reruns tasks with and without Kompactor.

## Code graph

![Code graph: module map and a query](https://raw.githubusercontent.com/amarkum/kompactor/main/docs/dashboard-graph.png)

A local index of your repo (Python, Go, TypeScript, JavaScript, React), built in about a second and refreshed in the background. Nothing is sent anywhere and nothing is written to the repo.

```
kompactor graph query "session cookie"     find code by topic, with line ranges and who uses it
kompactor graph impact createStore         what uses it, and which tests to run
kompactor graph explain Name               one symbol: signature, callers, callees, tests
kompactor graph report                     core modules, entry points, import cycles
kompactor graph unused                     dead-code candidates
```

Supported languages and what Kompactor knows about each: [docs/languages.md](https://github.com/amarkum/kompactor/blob/main/docs/languages.md).

## Use it across a team

![Share with your team: the dashboard's Setup panel](https://raw.githubusercontent.com/amarkum/kompactor/main/docs/dashboard-team.png)

**Turn it on for everyone who works in a repo.** Commit this as `.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": {
    "kompactor": { "source": { "source": "github", "repo": "amarkum/kompactor" }, "autoUpdate": true }
  },
  "enabledPlugins": { "amarkum@kompactor": true }
}
```
When a teammate trusts the folder, Claude Code installs the plugin; each person then runs `/kompactor setup` once.

**Set the team's level for a repo** with a committed `.kompactor.json`:
```json
{ "preset": 4, "overrides": { "never_compact": ["terraform plan"] } }
```

**Admins** can put the same keys in Claude Code's managed settings to roll it out to every machine. To control what your team runs, fork the repo and use `your-org/kompactor` in the commands above. The dashboard's **Guide** page covers rollout, settings and FAQs in more detail.

## Troubleshooting

| Problem | What to do |
|---|---|
| No savings line after replies | Restart Claude Code after setup, then run `kompactor doctor`: it checks the installation and shows recent hook errors. The dashboard's **Self-test** panel runs every hook once. |
| An output looks too short | Claude can fetch the original with `kompactor show <id>` (the id is in the shortened output), or search earlier outputs with `kompactor search "text"`. |
| A command should never be shortened | Add it to **Never compact these commands** on the dashboard, or in `.kompactor.json` (`"never_compact": ["terraform plan"]`). For a single run, start the command with `KOMPACTOR_RAW=1`. |
| Something seems off | `kompactor stop` turns Kompactor off at once; every hook also lets the original output through if it hits an error. Errors are logged to `~/.kompactor/hook-errors.log`. |
| The dashboard port is busy | `kompactor start` picks a free port by itself and prints the address. |

## Commands

```
kompactor                         status: on/off, level, savings, how to use it
kompactor setup                   connect to Claude Code (CLI + VS Code) and open the dashboard
kompactor start / stop            turn on (dashboard in the background) / pause
kompactor uninstall [--purge]     remove from Claude Code
kompactor presets                 list levels        kompactor config preset 4    change level
kompactor gain                    savings so far     kompactor estimate           replay past sessions
kompactor graph <action>          query, impact, explain, callers, deps, path, report, unused
kompactor show ID / search TEXT   the raw outputs Kompactor shortened
kompactor prove                   A/B test Kompactor in real Claude Code sessions
kompactor doctor                  check the installation
kompactor ui                      the dashboard, in the foreground
```

## Development

```bash
python -m unittest discover tests     # 80 tests, including the real shell prefix run as Claude Code runs it
node vscode/test/smoke.js             # VS Code extension against a mock API
./scripts/build-vsix.sh               # › dist/kompactor-<version>.vsix
python scripts/bump_version.py X.Y.Z  # bump every version; pushing to main publishes to PyPI
```

How Claude Code's hooks behave on success, failure and very long output, and why Kompactor uses a shell prefix rather than rewriting commands: [docs/SPEC.md](https://github.com/amarkum/kompactor/blob/main/docs/SPEC.md).

Kompactor was called Kompact until version 0.4; installing it replaces an old Kompact install's settings.

## Support and security

- **Questions, bugs and ideas:** [open an issue](https://github.com/amarkum/kompactor/issues).
- **Security problems:** please report them privately, as described in [SECURITY.md](https://github.com/amarkum/kompactor/blob/main/SECURITY.md).
- **Privacy:** [PRIVACY.md](https://github.com/amarkum/kompactor/blob/main/PRIVACY.md) explains what Kompactor stores and how to delete it.

[MIT License](https://github.com/amarkum/kompactor/blob/main/LICENSE)
