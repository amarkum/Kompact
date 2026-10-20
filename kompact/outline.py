"""Code skeletons, repo maps and symbol extraction - no dependencies.

Python is parsed with `ast`; other languages use declaration regexes plus
brace/indent matching, which is good enough for navigation (the agent can
always Read the exact lines afterwards).
"""

import ast
import os
import re
import subprocess
from pathlib import Path

SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".kts", ".scala",
              ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".rb", ".php", ".lua", ".dart", ".sh", ".vue",
              ".svelte", ".ex", ".exs"}

DECL = re.compile(
    r"^(?P<indent>\s*)(?:export\s+)?(?:default\s+)?(?:pub(?:\([^)]*\))?\s+)?(?:public\s+|private\s+|protected\s+|internal\s+"
    r"|static\s+|abstract\s+|final\s+|override\s+|open\s+|sealed\s+|data\s+|async\s+|unsafe\s+|inline\s+|virtual\s+)*"
    r"(?P<kind>class|interface|struct|enum|trait|impl|type|fn|func|function\*?|def|defp|defmodule|module|object|record"
    r"|protocol|extension|namespace|const|let|var|val)\s+(?P<rest>.*)$")
# Methods inside classes for JS/TS/Java/C#/Kotlin: `name(args) {` / `Type name(args) {`
METHOD = re.compile(r"^(?P<indent>\s+)(?:(?:public|private|protected|static|async|override|get|set|readonly|final"
                    r"|virtual|abstract|synchronized)\s+)*(?:[\w<>\[\],.?]+\s+)?(?P<name>#?[A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?"
                    r"\([^;]*\)\s*(?::\s*[^={]+)?\s*(?:throws [\w., ]+)?\{?\s*$")
NOT_METHOD = {"if", "for", "while", "switch", "catch", "return", "else", "do", "try", "function", "new", "await"}


def _sig_py(node, src_lines):
    line = src_lines[node.lineno - 1].strip()
    # include multi-line signatures up to the colon
    i = node.lineno
    while not line.rstrip().endswith(":") and i < len(src_lines) and i < node.lineno + 8:
        line += " " + src_lines[i].strip()
        i += 1
    return re.sub(r"\s+", " ", line)


def outline_python(src: str):
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []

    def walk(body, depth):
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(n)
                sig = "".join(f"@{ast.unparse(d)} " for d in n.decorator_list) + _sig_py(n, lines)
                if doc:
                    sig += f'  # {doc.strip().splitlines()[0][:80]}'
                out.append((n.lineno, n.end_lineno, depth, sig))
                if isinstance(n, ast.ClassDef):
                    walk(n.body, depth + 1)
            elif depth == 0 and isinstance(n, (ast.Assign, ast.AnnAssign)) and n.lineno == n.end_lineno:
                txt = lines[n.lineno - 1].strip()
                if re.match(r"^[A-Z_][A-Z0-9_]*\s*[:=]", txt):  # module constants only
                    out.append((n.lineno, n.end_lineno, depth, txt[:120]))
    walk(tree.body, 0)
    return out


def _depth(ws: str, unit: int) -> int:
    return ws.count("\t") + ws.count(" ") // unit


def outline_generic(src: str):
    out = []
    lines = src.splitlines()
    spaces = [len(ln) - len(ln.lstrip(" ")) for ln in lines if ln.startswith(" ") and ln.strip()]
    unit = min([n for n in spaces if n >= 2] or [4])
    for i, ln in enumerate(lines, 1):
        if len(ln) > 400:
            continue
        m = DECL.match(ln)
        if m:
            kind, indent = m.group("kind"), _depth(m.group("indent"), unit)
            if (kind in ("const", "let", "var", "val") and indent > 0) or ln.rstrip().endswith(","):
                continue
            if kind in ("const", "let", "var", "val") and not re.search(r"=\s*(async\s*)?(\(|function|\w+\s*=>|class|\{$|\[$|new |require|import|styled|create)", ln):
                if not re.match(r"^\s*(export\s+)?const [A-Z_][A-Z0-9_]*\s*[=:]", ln):
                    continue
            out.append((i, _block_end(lines, i), indent, _clip(ln)))
            continue
        mm = METHOD.match(ln)
        if mm and mm.group("name") not in NOT_METHOD and ln.rstrip().endswith("{"):
            out.append((i, _block_end(lines, i), _depth(mm.group("indent"), unit), _clip(ln)))
    return out


def _clip(ln: str) -> str:
    s = ln.strip().rstrip("{").rstrip()
    return s if len(s) <= 160 else s[:157] + "..."


def _block_end(lines, start):
    """1-based end line of the block starting at `start` (brace or indent based)."""
    depth, seen = 0, False
    for j in range(start - 1, min(len(lines), start + 5000)):
        code = re.sub(r"(\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'|`[^`]*`|//.*$)", "", lines[j])
        depth += code.count("{") - code.count("}")
        seen |= "{" in code
        if seen and depth <= 0:
            return j + 1
        if not seen and code.rstrip().endswith(";"):
            return j + 1
        if not seen and j >= start:  # no brace on the declaration line or the next one
            break
    # indentation-based languages (ruby/elixir/lua `end`, or none)
    base = len(lines[start - 1]) - len(lines[start - 1].lstrip())
    for j in range(start, len(lines)):
        s = lines[j]
        if s.strip() and len(s) - len(s.lstrip()) <= base:
            return j + (1 if s.strip() in ("end", "}", "};") else 0)
    return len(lines)


def outline(path: str, src: str = None):
    """List of (start, end, depth, signature) for a file."""
    if src is None:
        src = Path(path).read_text(errors="replace")
    if path.endswith(".py"):
        try:
            return outline_python(src)
        except SyntaxError:
            pass
    return outline_generic(src)


def render_outline(path: str, src: str = None, max_items: int = 400) -> str:
    items = outline(path, src)
    rows = [f"{'  ' * d}{sig}  [L{s}-{e}]" if e and e > s else f"{'  ' * d}{sig}  [L{s}]"
            for s, e, d, sig in items[:max_items]]
    if len(items) > max_items:
        rows.append(f"… +{len(items) - max_items} more symbols")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# repo map


IGNORE_DIRS = {".git", "node_modules", "dist", "build", "out", "target", "vendor", ".venv", "venv", "__pycache__",
               ".next", ".nuxt", "coverage", ".mypy_cache", ".pytest_cache", ".tox", ".idea", ".gradle"}


def list_files(root: str):
    try:
        res = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=root, capture_output=True,
                             text=True, timeout=20)
        if res.returncode == 0:
            return [f for f in res.stdout.splitlines() if f]
    except (OSError, subprocess.TimeoutExpired):
        pass
    files = []
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in IGNORE_DIRS and not x.startswith(".")]
        files += [os.path.relpath(os.path.join(d, f), root) for f in fs]
    return files


TESTY = re.compile(r"(^|/)(tests?|__tests__|test-d|spec|specs|fixtures?|examples?|e2e|benchmarks?)(/|$)|[._-](test|spec)\.\w+$|(^|/)test_[^/]+$")


def _mappable(path: str, sig: str) -> bool:
    """In JS/TS only exported values make the map; locals are noise there."""
    if Path(path).suffix in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs") and re.match(r"(const|let|var)\s", sig):
        return False
    return True


def repo_map(root: str = ".", budget_tokens: int = 4000, depth_limit: int = 1) -> str:
    """Compact map of every source file's top-level symbols, trimmed to a token budget.

    Files are ordered by how often their symbols are referenced elsewhere (a cheap
    PageRank stand-in), so the most central code survives trimming.
    """
    from . import tokens

    files = [f for f in list_files(root) if Path(f).suffix in SOURCE_EXT]
    entries, words = [], {}
    for f in files:
        p = os.path.join(root, f)
        try:
            if os.path.getsize(p) > 400_000:
                continue
            src = Path(p).read_text(errors="replace")
        except OSError:
            continue
        words[f] = set(re.findall(r"[A-Za-z_]\w{3,}", src))
        items = [it for it in outline(f, src) if it[2] <= depth_limit and _mappable(f, it[3])]
        entries.append((f, items))

    # rank files by how many *other* files reference the symbols they define
    defined = {}
    for f, items in entries:
        for _, _, _, sig in items:
            m = re.search(r"(?:def|class|function|func|fn|interface|struct|type|enum|trait|const|let|var)\s+\*?([A-Za-z_]\w{3,})", sig)
            if m:
                defined.setdefault(m.group(1), set()).add(f)
    score = {f: 0.0 for f, _ in entries}
    for name, owners in defined.items():
        users = sum(1 for f, ws in words.items() if name in ws and f not in owners)
        for f in owners:
            score[f] += users
    for f in score:
        if TESTY.search(f):
            score[f] = score[f] * 0.05 - 1

    entries.sort(key=lambda e: (-score[e[0]], e[0]))
    out, used = [], 0
    skipped = []
    for f, items in entries:
        block = [f"{f}:"] + [f"  {'  ' * d}{sig}" for _, _, d, sig in items[:60]]
        if len(items) > 60:
            block.append(f"  … +{len(items) - 60} more")
        cost = tokens.count("\n".join(block))
        if used + cost > budget_tokens and out:
            skipped.append(f)
            continue
        out += block
        used += cost
    if skipped:
        out.append(f"[{len(skipped)} lower-ranked files omitted to fit budget: {', '.join(skipped[:15])}"
                   f"{' …' if len(skipped) > 15 else ''}]")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# symbol lookup


NAME = re.compile(r"\b(?:def|class|function\*?|func|fn|interface|struct|type|enum|trait|const|let|var|val|impl|module"
                  r"|object|record|protocol|namespace|defp?|defmodule)\s+(?:\([^)]*\)\s*)?\*?([A-Za-z_$][\w$.]*)")


def _name(sig: str):
    sig = re.sub(r"^(@\S+(\([^)]*\))?\s+)+", "", sig)
    m = NAME.search(sig)
    if m:
        return m.group(1).split(".")[-1]
    m = re.match(r"^(?:[\w<>\[\],.?]+\s+)*([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\(", sig)
    return m.group(1) if m else None


def find_symbol(name: str, root: str = ".", paths=None, max_hits: int = 5):
    """Yield (file, start, end, source) for definitions named `name` (supports Class.method)."""
    parts = name.split(".")
    leaf = parts[-1]
    hits = []
    for f in paths or list_files(root):
        if Path(f).suffix not in SOURCE_EXT:
            continue
        p = f if os.path.isabs(f) else os.path.join(root, f)
        try:
            src = Path(p).read_text(errors="replace")
        except OSError:
            continue
        if leaf not in src:
            continue
        lines = src.splitlines()
        items = outline(f, src)
        for idx, (s, e, d, sig) in enumerate(items):
            if _name(sig) != leaf:
                continue
            if len(parts) > 1:  # require an enclosing parent with the given name
                parents = [it for it in items[:idx] if it[2] < d and it[0] <= s <= (it[1] or s)]
                if not parents or parts[-2] not in parents[-1][3]:
                    continue
            hits.append((f, s, e, "\n".join(lines[s - 1:e])))
            if len(hits) >= max_hits:
                return hits
    return hits
