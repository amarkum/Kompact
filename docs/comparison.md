# How Kompactor compares

[← Back to the README](../README.md)

Kompactor borrows the best idea from each of these tools: graphify's code graph, ponytail's lean-code ladder, caveman's terse prose, rtk's command filters, context-mode's raw-output stash, and the symbol-level reads of token-savior and code-review-graph. It then fixes the gaps that independent tests found. Researched in October 2026 from each project's repo and the independent tests linked below.

**Features** (Yes, Partly, or —):

| | Kompactor | [graphify](https://github.com/Graphify-Labs/graphify) | [ponytail](https://github.com/DietrichGebert/ponytail) | [caveman](https://github.com/JuliusBrussee/caveman) | [rtk](https://github.com/rtk-ai/rtk) | [token-savior](https://github.com/Mibayy/token-savior) | [context-mode](https://github.com/mksglu/context-mode) | [code-review-graph](https://github.com/tirth8205/code-review-graph) |
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
| **Kompactor** | Hooks act on every tool call, so Claude doesn't have to choose to use them | 0–177 tokens of rules + a 63-token skill entry | −16% tokens, −10% cost, 27/27 correct ([evidence](../README.md#evidence); self-run, reproducible with `kompactor prove`) |
| graphify | Nudges Claude to query the graph. An 87-session analysis found 4% of nudges followed; the nudges cost about 651k tokens against 176k from graphify's own answers ([#3435](https://github.com/Graphify-Labs/graphify/issues/3435)) | ~11k-token skill | 7.3× on code-only questions in one test. The 71.5× headline divided the whole corpus by one answer and has been dropped from its README |
| ponytail | Hooks inject its rules. As a plain skill it activated in 0 of 10 runs | Rules + a codebase map at each start | Cost −10.3%, code −15%, quality unchanged ([JetBrains](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/), ~80 tasks) |
| caveman | Hooks inject its rules | ~1,160 tokens | Output −8.5%, cost ≈ −10% per task ([JetBrains](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/)) |
| rtk | A hook rewrites commands; the rewrites bypass permission rules (rtk #4644) | None | Cost +7.6% at low effort, ±0% at high ([JetBrains](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/), 86 tasks). `rtk gain` counts all raw output, and reported 96.2M tokens saved while the bill rose |
| token-savior | Only when Claude calls its MCP tools: 1 of 143 sessions in a re-measurement it later withdrew | ~1.5k tokens of tool schemas (15 tools) and up | −43% tokens, −13% cost in one run ([computingforgeeks](https://computingforgeeks.com/reduce-claude-code-token-usage-tools/)) |
| context-mode | Hooks route big outputs into its sandbox; retrieval is via MCP | 11 tool schemas | No independent measurement found |
| code-review-graph | Only when Claude calls its MCP tools | 30 tool schemas | −5% in one run ([computingforgeeks](https://computingforgeeks.com/reduce-claude-code-token-usage-tools/)) |

**Where Kompactor is better**
- **It works without being asked.** Graph tools and MCP servers save nothing when Claude doesn't call them, and the data above shows how often that happens. Kompactor's savings come from hooks on every tool call. In the A/B runs, Claude never had to run a Kompactor command for them to apply.
- **It handles the failing run.** That's where the noisiest output is, and where Claude Code itself drops the useful part. rtk handles failures too, but by rewriting commands, which bypasses your permission rules. Kompactor acts after the permission check, on Claude's original command, with the exit code unchanged.
- **Its own instructions are small.** 156 tokens at the default level, against ~1,160 for caveman and an ~11k-token skill for graphify. The code map only appears once Claude starts exploring code.
- **Its savings numbers are honest.** It counts what Claude would actually have read, not raw output size, and it reverses a saving when Claude reads the full file anyway.
- **It's proven on cost and correctness, not just token counts.** `kompactor prove` reruns the same tasks with and without Kompactor in real Claude Code sessions, and the results are in this repo.
- **One control covers every layer**, from a dashboard, with a live preview of exactly what Claude would see.

**Where others are stronger**
- graphify builds a multimodal graph: docs, PDFs and images through an LLM, about 40 languages, Obsidian and Neo4j exports. Kompactor's graph covers code only: Python, Go, TypeScript, JavaScript, React, Rust, Java, Kotlin, Scala, C#, Swift, C, C++, Ruby and PHP.
- rtk has native filters for 100+ commands at under 10 ms each. Kompactor's filters cover the common dev commands and run in Python (50–100 ms per hook).
- context-mode runs code in a sandbox and indexes huge outputs such as Playwright snapshots. token-savior keeps memory across sessions. Kompactor does neither.

