# Changelog

All notable changes to Kompactor. Versions follow [semantic versioning](https://semver.org/).

## Unreleased

- Configuration: switch and setting changes apply to every level card, so switching compaction off lowers them all and they stay in order from Max quality to Max savings. Before, only the selected card changed.
- Configuration: a level card's "trimming & rules" figure combines what each technique that's on saved by itself in the benchmark (outline-first reads, short replies, lean-code rules; trimming and the code graph saved nothing measurable by themselves). Before, it used each level's own benchmark result, about 1% and within noise, so switching compaction off showed ≈0% on every card. The cards now read about 8, 21, 30, 44 and 57% lower cost with compaction, and 8, 12, 14, 14 and 14% without.
- Advanced settings shows only prose style and code style. The rest, the Claude Code display settings and the All configuration table are under "More settings", closed by default, which counts how many you've changed.

## 0.8.7

- Configuration shows approximate savings from Kompactor's benchmark, not from your own sessions. `bench/sessions.py` runs real headless Claude Code sessions on cobra (Go), Flask and click (Python) and zustand (TypeScript) in four lengths, from one command (about 2 turns) to twenty steps (about 27 turns): without Kompactor, at each level, and with each technique switched on by itself. Each level card shows one approximate cost saving, rising from Max quality to Max savings: the level's measured trimming and reply rules, plus compacting earlier at the level's size. Each switch shows what its technique saved by itself, and the cards and "Your settings" update as you pick a level, flip a switch or change a setting. Results are in `evidence/sessions`.
- Each technique measured on its own (`evidence/techniques`, 144 Claude Code sessions): short replies −8.5% cost and −21% reply tokens; lean-code rules, the code graph and trimming made no clear difference to cost by themselves in these short sessions. The Configuration page shows each figure with its 95% range on the technique's switch, and the techniques switched on combined, updating as you flip them.
- `kompactor prove` leaves out `~/.claude/settings.json` (`--setting-sources project,local`), so on a machine with Kompactor installed its hooks no longer run in the baseline arm.
- The selected level card's top edge is no longer clipped when the cards scroll sideways.

## 0.8.6

- Levels now cut cost where it's spent. Every request re-sends the whole conversation, and in long sessions that is most of the bill, so each level also sets how large the conversation may grow before Claude Code compacts it (Claude Code's `autoCompactWindow`): Max quality leaves Claude Code's default, Quality 780K, Balanced 650K, Savings 430K, Max savings 240K tokens. On 65 real Opus 5.5 sessions replayed with `kompactor estimate`, the levels save about 0, 10, 19, 35 and 50% of cost; trimming output alone saved under 2%. The window is set while Kompactor runs and removed by `kompactor stop` and `uninstall`; a window you set yourself with `/autocompact` or in settings is never changed. New setting: `compact_window`.
- Changing the level or the reply and code rules now reaches sessions that are already open: Claude gets the new rules with your next message (a `UserPromptSubmit` hook), instead of only in new sessions. Trimming and file-read settings already applied on the next tool call.
- Configuration: "What Kompactor does" has a switch for each technique: compacting the conversation earlier, trimming command output (rtk-style), outline-first reads, the code graph (graphify-style), lean-code rules (ponytail-style) and short replies (caveman-style), each with what it saved on your past sessions where that can be measured. Switching one on goes back to the level's strength for it.
- `kompactor estimate` and the dashboard's replay simulate compacting earlier and report it next to the trimming saving. The Configuration page shows each level's estimated cost saving on your own past sessions.

- Dashboard Overview, reworked to be read at a glance: a one-sentence summary ("shortened tool output in 21 of Claude's 31 replies… worth $0.35 at Opus 5.5 API prices"), cards for tokens saved, dollars, output shortened and replies helped, and a "What do these numbers mean?" note.
- Claude's replies can be filtered by command or file (e.g. `pytest`), saving size, kind of saving and session, and sorted by newest, oldest, biggest saving or dollars. The chart and list show the matching replies, with what each one shortened and what it was worth; click one for its before and after.
- Before and after: the Overview shows real command outputs Kompactor shortened, line by line, next to exactly what Claude was given. Long runs of removed lines fold into "⋯ 323 more removed lines", which opens on click. It replaces the live preview, which showed what Claude would get rather than what it got.
- "Quality vs tokens" is now **Configuration**, with clearer level cards (strength, what each level does, savings on your outputs). "Projects & languages" is now **Projects**.
- Languages are always detected from each repo's files. The "Always use" switch is gone, and a list pinned with it before is ignored.
- The light/dark switch is one icon in the top-right corner. Copy buttons in the Guide and Setup are an icon in the corner that shows on hover. Project paths are shown in full, cut with "…" at the start when they're long.

- Evidence: `evidence/real-repos` measures compaction on real test suites, builds, git and grep output in 6 repositories (Python, TypeScript, C, Swift, Java), with planted failures: median −61% per output at Balanced, every planted failure line kept at levels 1, 3 and 5. `bench/real_repos.py` reproduces it.
- Fixed: at the Max savings level (lines clipped at 200 characters), an error line that starts with a long path lost its message at the end, so a failing `swift test` or a Java compile error could reach Claude without the actual failure. Error lines are now kept whole up to 2,000 characters and past that clipped in the middle. Found by the real-repository benchmark.
- Swift, Maven and Gradle output: XCTest's per-test started/passed lines and suite banners, Swift's build progress, Maven's plugin banners, routine [INFO] lines and fixed help footer, Gradle's up-to-date tasks and the JVM's sun.misc.Unsafe notices are dropped; failures, summaries and a test that started but never finished are kept. `swift`, `dotnet`, `mix` and `deno` builds and tests now go through the shell prefix, so their failing runs are compacted too. Found by the real-repository benchmark: `swift test` went from 2,779 to 244 tokens and a failing `mvn test` from 1,242 to 425, with the failure kept.
- `kompactor rules`: the reply and code rules plus code-graph tips for Cursor, Windsurf, Cline, Codex (`AGENTS.md`), GitHub Copilot, Gemini CLI and Aider, in each one's rules file. Shared files get a marked block that is updated in place; `--remove` takes it out.
- Choose which subagents get the reply and code rules: a pattern matched against the subagent's type (dashboard setting or `KOMPACTOR_SUBAGENT_MATCHER`, e.g. `explore|general`). Subagents whose type isn't reported, or a bad pattern, still get them.
- Fixed: the dashboard saved "Keep history for" as true/false, so changing it could prune history older than 1 day instead of the chosen number. General settings now keep their types, and an old true/false value falls back to 30 days.
- Docs in the code graph: Markdown and reStructuredText headings become searchable sections, and backticked names, paths and local links tie them to the code. `graph impact` lists "docs that mention it" and `graph explain` adds "documented in". Docs never count as modules, areas or callers.
- `kompactor graph export json|graphml|mermaid|obsidian`: the graph as data, for Gephi or yEd, as a Mermaid diagram grouped by area, or as an Obsidian vault. `kompactor graph hook install` adds a background graph refresh to the repo's post-commit, post-merge and post-checkout hooks, beside any hooks already there (`uninstall` removes only its own line).
- Callers and `explain` label each link: exact (same module, or it imports the definition), likely (the only definition of that name), ambiguous (several definitions, none imported) or external (not defined in the repo), with a count per label.
- Code graph communities: modules that import each other are grouped into areas (label propagation over the import graph, folder-mates weighted a little higher). `graph report` lists them with their hub; the dashboard's module map colours nodes by area with a named legend.
- `kompactor mcp`: an MCP server (stdio) with read-only tools for graph query, callers, impact, deps, explain, path, report, unused, outline and symbol, so any MCP client can use the code graph. `claude mcp add kompactor -- kompactor mcp`.
- Code graph for Rust, Java, Kotlin, Scala, C#, Swift, C, C++, Ruby and PHP: symbols, methods, visibility, doc comments, imports resolved to files, calls and inheritance. Each gets a language profile (detection, library stack frames, generated and lock files) and test-file recognition. Existing graphs rebuild once.
- Dashboard: tool outputs passed to Claude unchanged are listed with why; every project appears in the picker; each turn can be previewed (raw output and what Claude saw); the live preview and level figures use your own latest outputs only; delete history by project and time range; an All configuration reference; dates like "22nd Oct 2026, 6:24 PM".

## 0.8.5

- Dollars saved are worked out at the API price of the model each session ran on (read from the status line: Opus 5.5 $4 per million input, cache writes $5, cache reads $0.20), instead of a flat $3.
- Each saved token is counted once as a prompt-cache write and again at the cache-read price for every later request that would have re-read it (one per tool call and one per new prompt), stopping at compaction. Before, only later turns were counted, and compaction was ignored.
- VS Code / Cursor: amounts show to the cent or a hundredth of a cent, each recent reply shows what it saved in dollars, and the note names the prices used. `kompactor.pricePerMillionTokens` now defaults to 0 (use the model's price); set it to override.
- `kompactor gain` prints the dollar figure.

## 0.8.4

- Status: savings read "2.7k tokens (−44%)" instead of "( 44.4%)".

## 0.8.3

- `kompactor help` (and `-h`, `--help`) is a short, standard help page grouped by task; internal commands are hidden.
- A mistyped command suggests the closest one ("Did you mean this? kompactor start") instead of printing every command.
- Plain `kompactor` shows a compact, aligned status summary.
- VS Code / Cursor sidebar: "Recent replies" shows what Kompactor shortened in each of Claude's replies (commands and files, e.g. `pytest -v ×2`) instead of numbered turns, and folds replies with nothing to shorten into one line.

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
