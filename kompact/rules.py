"""Reply-style rules injected at session start (and into subagents).

Two independent dials, kept deliberately short because these tokens are paid
on every turn (caveman's rules cost ~1,160; these cost ~60-180):

- prose: off | lite | full | ultra   (caveman / claude-token-efficient lineage)
- code:  normal | lean | strict      (ponytail lineage: reuse first, smallest diff)

Code, commands, paths, errors, numbers, negations and security warnings are
never shortened, and commit messages and docs stay normal prose.
"""

ANSWER_FIRST = "Lead with the answer; no preamble, recap, restated question or praise."
PROSE = {
    "off": [],
    "lite": [ANSWER_FIRST],
    "full": [ANSWER_FIRST, "Short sentences, fragments fine, lists over paragraphs; no narration between tool calls."],
    "ultra": [ANSWER_FIRST, "Telegraphic: one line per point, articles optional, no narration. Explain only if asked."],
}

LEAN = [
    "Before editing, check callers, tests and config (`{cli} graph impact <file|symbol>`).",
    "Prefer no change, then reuse (codebase, stdlib, installed packages), then the smallest diff. Fix root causes.",
    "No unrequested abstractions, options or refactors; one focused test for non-trivial logic.",
    "Never trade away validation, error handling, security or accessibility.",
]
CODE = {
    "normal": [],
    "lean": LEAN,
    "strict": LEAN + ["If a smaller alternative would do, propose it first. Mark deliberate limits `shortcut: <limit>`."],
}

KEEP = "Keep code, commands, paths, errors, numbers and warnings exact; commits and docs stay normal prose."

TOOLS = [
    "Compacted Bash output: `{cli} show <id>` prints it in full. Big files open as an outline; repeat the Read for all.",
    "Find code: `{cli} graph query \"words\"`, `{cli} symbol Name`.",
]


def build(prose: str = "lite", code: str = "lean", cli: str = "kompact", tools: bool = True) -> str:
    lines = list(PROSE.get(prose, []))
    if lines:
        lines.append(KEEP)
    lines += CODE.get(code, [])
    if tools:
        lines += TOOLS
    if not lines:
        return ""
    return "[kompact]\n" + "\n".join(f"- {ln.format(cli=cli)}" for ln in lines)


# Back-compat for callers that look up a style by name.
STYLES = {name: build(name, "normal", tools=name != "off") for name in PROSE}
