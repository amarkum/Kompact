"""Reply-style rules injected at session start (and into subagents).

Two independent dials, kept deliberately short because these tokens are paid
on every turn (caveman's rules cost ~1,160; these cost ~20-160). Kompactor's own
commands aren't advertised here: compacted output and outlines say how to get
the full text, and the code map (given on first exploration) names the graph.

- prose: off | lite | full | ultra   (caveman / claude-token-efficient lineage)
- code:  normal | lean | strict      (ponytail lineage: reuse first, smallest diff)

Code, commands, paths, errors, numbers, negations and security warnings are
never shortened, and commit messages and docs stay normal prose.
"""

from pathlib import Path

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

PLAIN = ("Run tests, builds and linters plainly, without | head, | tail or | grep: Kompactor keeps every failure, "
         "so one run is enough.")


def build(prose: str = "lite", code: str = "lean", cli: str = "kompactor", plain: bool = False) -> str:
    lines = list(PROSE.get(prose, []))
    if lines:
        lines.append(KEEP)
    lines += CODE.get(code, [])
    if plain:
        lines.append(PLAIN)
    if not lines:
        return ""
    return "[kompactor]\n" + "\n".join(f"- {ln.format(cli=cli)}" for ln in lines)


# Back-compat for callers that look up a style by name.
STYLES = {name: build(name, "normal") for name in PROSE}


# ---------------------------------------------------------------------------
# rules files for other coding agents: `kompactor rules --agent cursor`

# agent -> (file in the repo, whether Kompactor owns the whole file or a marked block in a shared one)
AGENT_FILES = {
    "cursor": (".cursor/rules/kompactor.mdc", "own"),
    "windsurf": (".windsurf/rules/kompactor.md", "own"),
    "cline": (".clinerules/kompactor.md", "own"),
    "codex": ("AGENTS.md", "block"),
    "copilot": (".github/copilot-instructions.md", "block"),
    "gemini": ("GEMINI.md", "block"),
    "aider": ("CONVENTIONS.md", "block"),
}
BEGIN, END = "<!-- kompactor:start -->", "<!-- kompactor:end -->"


def agent_text(prose: str, code: str, cli: str = "kompactor") -> str:
    """The rules plus how to use the code graph, for agents Kompactor has no hooks in."""
    rules = build(prose, code, cli).replace("[kompactor]\n", "")
    graph = [f"- Find code by topic before searching or reading files: `{cli} graph query \"words\"`.",
             f"- One definition without the rest of its file: `{cli} symbol Name` (or `Class.method`); a file's "
             f"structure with line ranges: `{cli} outline <file>`.",
             f"- Before changing code: `{cli} graph impact <file|symbol>` for what depends on it, the tests to run "
             f"and the docs to update; `{cli} graph callers <name>` for who calls it.",
             f"- The same tools over MCP: `{cli} mcp`."]
    return "## Kompactor\n\n" + (rules + "\n\n" if rules else "") + "### Code graph\n\n" + "\n".join(graph) + "\n"


def write_agent_rules(root: str, agents, prose: str = "lite", code: str = "lean", cli: str = "kompactor",
                      remove: bool = False) -> list:
    """Write (or remove) Kompactor's rules in each agent's rules file under `root`. Returns the files changed."""
    import re
    changed = []
    for agent in agents:
        rel, mode = AGENT_FILES[agent]
        p = Path(root, rel)
        old = p.read_text() if p.exists() else ""
        body = agent_text(prose, code, cli)
        if mode == "own":
            if remove:
                if p.exists():
                    p.unlink()
                    changed.append(str(p))
                continue
            if agent == "cursor":
                body = "---\ndescription: Kompactor rules and code graph\nalwaysApply: true\n---\n\n" + body
            new = body
        else:
            block = f"{BEGIN}\n{body}{END}\n"
            if BEGIN in old and remove:
                new = re.sub(r"\n*" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "\n", old, flags=re.S)
                new = new.lstrip("\n") if not new.strip() else new
            elif BEGIN in old:
                new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", lambda m: block, old, flags=re.S)
            elif remove:
                continue
            else:
                new = old + ("\n" if old and not old.endswith("\n") else "") + ("\n" if old else "") + block
            if remove and not new.strip():
                p.unlink()
                changed.append(str(p))
                continue
        if new != old:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new)
            changed.append(str(p))
    return changed
