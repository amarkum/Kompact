"""Output-style rules injected at session start.

Distilled from caveman (terse prose), ponytail (minimal code) and
claude-token-efficient (agent habits). Kept short on purpose: these tokens are
paid on every turn, so the rules themselves must be cheap.
"""

LITE = """\
[kompact] Token discipline:
- No preamble, no recap of what you just did, no restating the question. Lead with the answer.
- Code, commands, paths and error text stay exact; trim the prose around them.
- Read big files with offset/limit or `kompact outline <file>` / `kompact symbol <name>` first.
- Don't re-read files you already have in context. Prefer Edit over rewriting whole files.
- Bash output may be compacted; `kompact show <id>` prints the full raw output when a note says so."""

FULL = LITE + """
- Fragments are fine. Drop articles, hedges and pleasantries.
- Write the least code that solves the task: no speculative abstractions, options, or comments restating code.
- Don't add tests, docs or refactors that weren't asked for; offer them in one line instead.
- For orientation use `kompact map` (ranked repo skeleton) instead of listing and reading many files."""

STYLES = {"off": "", "lite": LITE, "full": FULL}
