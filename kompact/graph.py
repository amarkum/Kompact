"""Code graph: files, symbols and the references between them.

Standard library only. Python is parsed with `ast`; Go and TypeScript /
JavaScript / React with targeted regexes over comment- and string-free source.
The graph lives in SQLite per project and is updated incrementally: only files
whose mtime or size changed are re-parsed.

Units: a Python or TS/JS module is one file; a Go package is one directory.
Edges between units come from resolved imports; symbol references (calls, JSX
renders, inheritance) are stored by name and resolved at query time.
"""

import ast
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

from . import langs, outline, store, tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY, lang TEXT, unit TEXT, mtime_ns INTEGER, size INTEGER, lines INTEGER,
    is_test INTEGER, is_generated INTEGER
);
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY, file TEXT, name TEXT, kind TEXT, parent TEXT, start INTEGER, end INTEGER,
    signature TEXT, doc TEXT, exported INTEGER
);
CREATE INDEX IF NOT EXISTS symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS symbols_file ON symbols(file);
CREATE TABLE IF NOT EXISTS refs (file TEXT, scope TEXT, name TEXT, kind TEXT, line INTEGER);
CREATE INDEX IF NOT EXISTS refs_name ON refs(name);
CREATE INDEX IF NOT EXISTS refs_file ON refs(file);
CREATE TABLE IF NOT EXISTS imports (file TEXT, target TEXT, resolved TEXT, names TEXT, type_only INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS idents (file TEXT, name TEXT, count INTEGER);
CREATE INDEX IF NOT EXISTS idents_name ON idents(name);
CREATE INDEX IF NOT EXISTS imports_file ON imports(file);
CREATE INDEX IF NOT EXISTS imports_resolved ON imports(resolved);
"""

LANG_OF = {".py": "python", ".pyi": "python", ".go": "go", ".ts": "ts", ".tsx": "ts", ".js": "ts", ".jsx": "ts",
           ".mjs": "ts", ".cjs": "ts", ".mts": "ts", ".cts": "ts"}
MAX_FILE_BYTES = 600_000
TEST_FILE = re.compile(r"(^|/)(tests?|__tests__|test-d|spec|specs|e2e|testdata)(/|$)|[._-](test|spec)\.\w+$|"
                       r"(^|/)test_[^/]+\.py$|_test\.go$|(^|/)conftest\.py$")
AUX_FILE = re.compile(r"(^|/)(examples?|docs?|benchmarks?|bench|scripts?|fixtures?|demo|samples?)(/|$)")

# ---------------------------------------------------------------------------
# storage


def db_path(root: str) -> Path:
    root = str(Path(root).resolve())
    name = re.sub(r"[^\w.-]", "_", Path(root).name)[:40] or "root"
    d = store.home() / "graphs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}-{hashlib.sha1(root.encode()).hexdigest()[:10]}.db"


class _Conn(sqlite3.Connection):
    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            self.close()


SCHEMA_VERSION = "3"


def connect(root: str) -> _Conn:
    path = db_path(root)
    if path.exists():  # the graph is a cache: rebuild it when the schema changes
        try:
            with sqlite3.connect(path) as probe:
                row = probe.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
            if not row or row[0] != SCHEMA_VERSION:
                for suffix in ("", "-wal", "-shm"):
                    Path(str(path) + suffix).unlink(missing_ok=True)
        except sqlite3.Error:
            path.unlink(missing_ok=True)
    db = sqlite3.connect(path, timeout=20, factory=_Conn)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO meta VALUES ('schema', ?)", (SCHEMA_VERSION,))
    return db


def exists(root: str) -> bool:
    p = db_path(root)
    if not p.exists():
        return False
    with connect(root) as db:
        return db.execute("SELECT value FROM meta WHERE key='built'").fetchone() is not None


# ---------------------------------------------------------------------------
# helpers

_COMMENT_STRING = re.compile(
    r"//[^\n]*|/\*.*?\*/|`(?:\\.|[^`\\])*`|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", re.S)


def _blank(src: str) -> str:
    """Replace comments and string literals with spaces, keeping line numbers."""
    return _COMMENT_STRING.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), src)


def _first_doc_line(text: str) -> str:
    for ln in (text or "").strip().splitlines():
        ln = ln.strip().strip("/*# ").strip()
        if ln:
            return ln[:120]
    return ""


def _scope_at(spans, line: int) -> str:
    """Innermost symbol (by span) containing a line."""
    best, size = "", 1 << 30
    for start, end, qual in spans:
        if start <= line <= end and end - start < size:
            best, size = qual, end - start
    return best


def split_words(name: str):
    """camelCase / snake_case / kebab-case -> lowercase words."""
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name))
    return [w.lower() for w in re.split(r"[^A-Za-z0-9]+", parts) if w]


# ---------------------------------------------------------------------------
# Python


def _py_sig(node, lines):
    strip = lambda ln: re.sub(r"\s+#.*$", "", ln).strip()  # noqa: E731  (drop trailing comments)
    head = strip(lines[node.lineno - 1])
    i = node.lineno
    while not head.endswith(":") and i < len(lines) and i < node.lineno + 8:
        head += " " + strip(lines[i])
        i += 1
    return re.sub(r"\s+", " ", head)[:200]


def _attr_tail(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _attr_tail(node.func)
    if isinstance(node, ast.Subscript):
        return _attr_tail(node.value)
    return None


def _is_type_checking(test) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or \
        (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")


def parse_python(path: str, src: str):
    tree = ast.parse(src)
    lines = src.splitlines()
    syms, refs, imps, alias = [], [], [], {}
    type_only = [0]

    def walk(node, scope, cls):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, ast.If) and _is_type_checking(n.test):
                type_only[0] += 1
                for child in n.body:
                    walk(ast.Module(body=[child], type_ignores=[]), scope, cls)
                type_only[0] -= 1
                for child in n.orelse:
                    walk(ast.Module(body=[child], type_ignores=[]), scope, cls)
                continue
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nested = bool(scope) and not cls  # a def inside a function body
                qual = f"{cls}.{n.name}" if cls else (f"{scope}.{n.name}" if nested else n.name)
                deco = "".join(f"@{_attr_tail(d) or ast.unparse(d)} " for d in n.decorator_list)
                syms.append((n.name, "method" if cls else "function", cls or (scope if nested else ""), n.lineno,
                             n.end_lineno, deco + _py_sig(n, lines), _first_doc_line(ast.get_docstring(n) or ""),
                             int(not n.name.startswith("_") and not nested)))
                for d in n.decorator_list:
                    t = _attr_tail(d)
                    if t:
                        refs.append((qual, alias.get(t, t), "decorate", n.lineno))
                walk(n, qual, None)
            elif isinstance(n, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in n.bases)
                syms.append((n.name, "class", cls or "", n.lineno, n.end_lineno,
                             f"class {n.name}({bases})" if bases else f"class {n.name}",
                             _first_doc_line(ast.get_docstring(n) or ""), int(not n.name.startswith("_"))))
                for b in n.bases:
                    t = _attr_tail(b)
                    if t:
                        refs.append((n.name, alias.get(t, t), "inherit", n.lineno))
                walk(n, n.name, n.name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    imps.append((a.name, 0, "", int(type_only[0] > 0)))
                    alias[a.asname or a.name.split(".")[0]] = a.name.split(".")[-1]
                walk(n, scope, cls)
            elif isinstance(n, ast.ImportFrom):
                names = [a.name for a in n.names]
                imps.append((n.module or "", n.level, ",".join(names), int(type_only[0] > 0)))
                for a in n.names:
                    if a.asname:
                        alias[a.asname] = a.name
                walk(n, scope, cls)
            else:
                if isinstance(n, ast.Call):
                    t = _attr_tail(n.func)
                    if t:
                        refs.append((scope, alias.get(t, t), "call", n.lineno))
                walk(n, scope, cls)

    walk(tree, "", None)
    idents = Counter()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            idents[n.id] += 1
        elif isinstance(n, ast.Attribute):
            idents[n.attr] += 1
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            idents[n.name] += 1
        elif isinstance(n, ast.alias):
            idents[n.name.split(".")[-1]] += 1
            if n.asname:
                idents[n.asname] += 1
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"[A-Za-z_]\w*", n.value):
            idents[n.value] += 1  # __all__ entries, getattr(obj, "name"), string registries
    IDENTS[path] = idents
    for n in tree.body:  # module-level CONSTANTS are symbols too
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                if isinstance(t, ast.Name) and re.match(r"^[A-Z][A-Z0-9_]+$", t.id):
                    syms.append((t.id, "constant", "", n.lineno, n.end_lineno, lines[n.lineno - 1].strip()[:160], "",
                                 int(not t.id.startswith("_"))))
    return syms, refs, imps


def _py_module(rel: str) -> str:
    mod = rel[:-3] if rel.endswith(".py") else rel[:-4] if rel.endswith(".pyi") else rel
    mod = mod.replace("/", ".")
    return mod[:-9] if mod.endswith(".__init__") else mod


# ---------------------------------------------------------------------------
# Go

GO_FUNC = re.compile(r"^func\s+(?:\(\s*\w*\s*\*?\s*([\w]+)(?:\[[^\]]*\])?\s*\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\(",
                     re.M)
GO_TYPE = re.compile(r"^(?:type\s+|\t)([A-Za-z_]\w*)(?:\[[^\]]*\])?\s+(struct|interface)\b", re.M)
GO_TYPE_ALIAS = re.compile(r"^type\s+([A-Za-z_]\w*)\s+(?!struct|interface)([\w.*\[\]]+)", re.M)
GO_IMPORT_ONE = re.compile(r'^import\s+(?:([\w.]+)\s+)?"([^"]+)"', re.M)
GO_IMPORT_BLOCK = re.compile(r"^import\s*\((.*?)^\)", re.M | re.S)
GO_IMPORT_LINE = re.compile(r'^\s*(?:([\w.]+)\s+)?"([^"]+)"', re.M)
GO_KEYWORDS = {"if", "for", "switch", "func", "return", "make", "len", "append", "cap", "new", "panic", "recover",
               "print", "println", "copy", "delete", "close", "complex", "real", "imag", "string", "int", "int64",
               "int32", "uint", "uint64", "uint32", "byte", "rune", "float64", "float32", "bool", "error", "select",
               "go", "defer", "range", "map", "chan", "struct", "interface", "type", "var", "const", "min", "max",
               "clear", "uintptr", "any"}


IDENTS = {}  # path -> Counter of identifier occurrences, filled by the parsers
IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def _regex_idents(path: str, clean: str, src: str) -> None:
    counts = Counter(IDENT.findall(clean))
    for lit in re.findall(r"""["'`]([A-Za-z_$][\w$]*)["'`]""", src):  # string registries / reflection
        counts[lit] += 1
    IDENTS[path] = counts


def parse_go(path: str, src: str):
    lines = src.splitlines()
    clean = _blank(src)
    _regex_idents(path, clean, src)
    syms, refs, imps = [], [], []
    for m in GO_IMPORT_ONE.finditer(src):
        imps.append((m.group(2), 0, m.group(1) or "", 0))
    for b in GO_IMPORT_BLOCK.finditer(src):
        for m in GO_IMPORT_LINE.finditer(b.group(1)):
            imps.append((m.group(2), 0, m.group(1) or "", 0))
    aliases = {}
    for target, _, al, _ in imps:
        aliases[al or target.rstrip("/").split("/")[-1]] = target
    spans = []
    for m in GO_FUNC.finditer(clean):
        line = clean.count("\n", 0, m.start()) + 1
        recv, name = m.group(1), m.group(2)
        end = outline._block_end(lines, line)
        qual = f"{recv}.{name}" if recv else name
        doc = _go_doc(lines, line)
        syms.append((name, "method" if recv else "function", recv or "", line, end, lines[line - 1].strip().rstrip("{").strip()[:200],
                     doc, int(name[:1].isupper())))
        spans.append((line, end, qual))
    for m in GO_TYPE.finditer(clean):
        line = clean.count("\n", 0, m.start()) + 1
        end = outline._block_end(lines, line)
        syms.append((m.group(1), m.group(2), "", line, end, lines[line - 1].strip().rstrip("{").strip()[:200],
                     _go_doc(lines, line), int(m.group(1)[:1].isupper())))
    for m in GO_TYPE_ALIAS.finditer(clean):
        line = clean.count("\n", 0, m.start()) + 1
        syms.append((m.group(1), "type", "", line, line, lines[line - 1].strip()[:200], _go_doc(lines, line),
                     int(m.group(1)[:1].isupper())))
    for i, ln in enumerate(clean.splitlines(), 1):
        scope = None
        for m in re.finditer(r"(?<![\w.])([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(", ln):
            scope = scope if scope is not None else _scope_at(spans, i)
            refs.append((scope, m.group(2), "call", i))
        for m in re.finditer(r"(?<![\w.])([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*\(", ln):
            name = m.group(1)
            if name in GO_KEYWORDS or ln.lstrip().startswith("func ") and ln.find(name) < ln.find("("):
                continue
            scope = scope if scope is not None else _scope_at(spans, i)
            refs.append((scope, name, "call", i))
        for m in re.finditer(r"&?([A-Z]\w*)\s*\{", ln):
            scope = scope if scope is not None else _scope_at(spans, i)
            refs.append((scope, m.group(1), "use", i))
    return syms, refs, imps


def _go_doc(lines, line):
    i, doc = line - 2, []
    while i >= 0 and lines[i].strip().startswith("//"):
        doc.insert(0, lines[i].strip()[2:].strip())
        i -= 1
    return doc[0][:120] if doc else ""


# ---------------------------------------------------------------------------
# TypeScript / JavaScript / React

TS_IMPORT = re.compile(r"""(?:^|[;\s])(?:import|export)\s+(type\s+)?(?:([\w*{}\s,$]+?)\s+from\s+)?['"]([^'"\n]+)['"]""",
                       re.M)
TS_REQUIRE = re.compile(r"""(?:require|import)\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
TS_KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "typeof", "new", "await", "super", "import",
               "export", "delete", "void", "yield", "in", "of", "else", "do", "try", "throw", "case", "async", "constructor",
               "Array", "Object", "String", "Number", "Boolean", "Promise", "Error", "Symbol", "Map", "Set", "JSON",
               "Math", "Date", "RegExp", "parseInt", "parseFloat", "require", "console", "describe", "it", "test",
               "expect", "beforeEach", "afterEach", "beforeAll", "afterAll", "get", "set", "as", "satisfies", "keyof"}
TS_DECL = re.compile(
    r"^(?P<ind>[ \t]*)(?P<exp>export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(?P<kind>function\*?|class|interface|type|enum|const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)", re.M)
TS_METHOD = re.compile(r"^(?P<ind>[ \t]+)(?:(?:public|private|protected|static|async|override|readonly|get|set|abstract)\s+)*"
                       r"(?P<name>#?[A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\([^;{]*\)\s*(?::\s*[^={;]+)?\s*\{\s*$", re.M)


def parse_ts(path: str, src: str):
    lines = src.splitlines()
    clean = _blank(src)
    _regex_idents(path, clean, src)
    clines = clean.splitlines()
    syms, refs, imps, spans = [], [], [], []
    for m in TS_IMPORT.finditer(src):
        imps.append((m.group(3), 0, _ts_import_names(m.group(2) or ""), int(bool(m.group(1)))))
    for m in TS_REQUIRE.finditer(src):
        imps.append((m.group(1), 0, "", 0))
    is_jsx = path.endswith((".tsx", ".jsx"))
    exported = set(re.findall(r"^export\s+default\s+([A-Za-z_$][\w$]*)\s*;?\s*$", clean, re.M))
    for m in re.finditer(r"^export\s*\{([^}]*)\}", clean, re.M):
        exported |= {p.split(" as ")[0].strip() for p in m.group(1).split(",") if p.strip()}
    for m in TS_DECL.finditer(clean):
        nested = len(m.group("ind").expandtabs(4)) > 0
        if nested and m.group("kind") in ("const", "let", "var"):
            continue
        line = clean.count("\n", 0, m.start()) + 1
        name, kind = m.group("name"), m.group("kind").rstrip("*")
        text = lines[line - 1]
        is_exported = (bool(m.group("exp")) or name in exported) and not nested
        if kind in ("const", "let", "var"):
            if re.search(r"=\s*(async\s*)?(\([^)]*\)|[\w$]+)\s*(:\s*[^=]+)?=>|=\s*(async\s+)?function\b|"
                         r"=\s*(React\.)?(memo|forwardRef|lazy)\(|=\s*styled[.(]|=\s*create\w*\(", text):
                kind = "function"
            elif re.search(r"=\s*[\w$.]+\s*(<[^>]*>)?\s*\(", text) and (
                    is_exported or re.match(r"use[A-Z]", name) or (is_jsx and name[:1].isupper())):
                kind = "function"  # factory-made: const useSWR = withArgs(handler)
            elif not is_exported:
                continue
            else:
                kind = "constant"
        if kind == "function" and name[:1].isupper() and is_jsx:
            kind = "component"
        elif kind == "function" and re.match(r"use[A-Z]", name):
            kind = "hook"
        end = outline._block_end(lines, line)
        if syms and syms[-1][0] == name and syms[-1][1] == kind == "function":
            syms.pop()  # TS overload signatures: keep the implementation (last) only
        syms.append((name, kind, "", line, end, text.strip().rstrip("{").strip()[:200], _ts_doc(lines, line),
                     int(is_exported)))
        spans.append((line, end, name))
    cls_spans = [(s[3], s[4], s[0]) for s in syms if s[1] == "class"]
    for m in TS_METHOD.finditer(clean):
        name = m.group("name")
        if name in TS_KEYWORDS and name != "constructor":
            continue
        line = clean.count("\n", 0, m.start()) + 1
        cls = _scope_at(cls_spans, line)
        if not cls:
            continue
        end = outline._block_end(lines, line)
        syms.append((name, "method", cls, line, end, lines[line - 1].strip().rstrip("{").strip()[:200],
                     _ts_doc(lines, line), int(not name.startswith(("#", "_")))))
        spans.append((line, end, f"{cls}.{name}"))
    for m in re.finditer(r"\bclass\s+(\w+)[^{\n]*?\b(extends|implements)\s+([\w$.]+)", clean):
        refs.append((m.group(1), m.group(3).split(".")[-1], "inherit", clean.count("\n", 0, m.start()) + 1))
    for i, ln in enumerate(clines, 1):
        scope = None
        for m in re.finditer(r"(?<![\w$])(?:\.\s*)?([A-Za-z_$][\w$]*)\s*(?:<[^<>()]*>)?\s*\(", ln):
            name = m.group(1)
            if name in TS_KEYWORDS:
                continue
            if re.match(r"\s*(export\s+)?(default\s+)?(async\s+)?function\b", ln) and ln.find(name) < ln.find("("):
                continue
            scope = scope if scope is not None else _scope_at(spans, i)
            refs.append((scope, name, "call", i))
        for m in re.finditer(r"<([A-Z][\w$]*)(?:\.[\w$]+)*[\s/>]", ln):
            scope = scope if scope is not None else _scope_at(spans, i)
            refs.append((scope, m.group(1), "render", i))
    return syms, refs, imps


def _ts_import_names(spec: str) -> str:
    names = []
    for part in re.split(r"[{},]", spec):
        part = part.strip()
        if not part or part.startswith("*"):
            continue
        names.append(part.split(" as ")[0].replace("type ", "").strip())
    return ",".join(n for n in names if n)


def _ts_doc(lines, line):
    i = line - 2
    while i >= 0 and lines[i].strip().startswith(("*", "/**", "//")):
        i -= 1
    block = "\n".join(lines[i + 1:line - 1])
    return _first_doc_line(re.sub(r"@\w+.*", "", block))


# ---------------------------------------------------------------------------
# resolution of imports to units


class Resolver:
    def __init__(self, root: str, files, all_paths=()):
        self.root = root
        self.files = set(files)
        self.ts_packages = []  # (package name, directory) for the repo and its workspaces
        for pj in all_paths:
            if os.path.basename(pj) == "package.json" and "node_modules/" not in pj:
                try:
                    name = json.loads(Path(root, pj).read_text(errors="replace")).get("name")
                except (OSError, ValueError, AttributeError):
                    continue
                if isinstance(name, str) and name:
                    self.ts_packages.append((name, os.path.dirname(pj)))
        self.ts_packages.sort(key=lambda x: -len(x[0]))
        self.py_index = {}
        # nested Python projects (monorepos, examples/): modules are importable relative to them
        dirs = set()
        for f in files:
            if f.endswith((".py", ".pyi")):
                d = os.path.dirname(f)
                while d and d not in dirs:
                    dirs.add(d)
                    d = os.path.dirname(d)
        py_roots = sorted((d for d in dirs if any(Path(root, d, m).exists() for m in ("pyproject.toml", "setup.py",
                                                                                      "setup.cfg"))),
                          key=len, reverse=True)
        for f in files:
            if f.endswith((".py", ".pyi")):
                mod = _py_module(f)
                self.py_index.setdefault(mod, f)
                for pr in py_roots:
                    if f.startswith(pr + "/"):
                        self.py_index.setdefault(_py_module(f[len(pr) + 1:]), f)
                for prefix in ("src.", "lib.", "python."):
                    for m in (mod, *(_py_module(f[len(pr) + 1:]) for pr in py_roots if f.startswith(pr + "/"))):
                        if m.startswith(prefix):
                            self.py_index.setdefault(m[len(prefix):], f)
        self.go_module = ""
        gm = Path(root, "go.mod")
        if gm.exists():
            m = re.search(r"^module\s+(\S+)", gm.read_text(errors="replace"), re.M)
            self.go_module = m.group(1) if m else ""
        self.go_dirs = {os.path.dirname(f) or "." for f in files if f.endswith(".go")}
        self.ts_paths = self._tsconfig_paths()

    def _tsconfig_paths(self):
        for name in ("tsconfig.json", "jsconfig.json", "tsconfig.base.json"):
            p = Path(self.root, name)
            if not p.exists():
                continue
            txt = re.sub(r"//[^\n]*|/\*.*?\*/", "", p.read_text(errors="replace"), flags=re.S)
            txt = re.sub(r",(\s*[}\]])", r"\1", txt)
            try:
                opts = json.loads(txt).get("compilerOptions", {})
            except ValueError:
                return []
            base = opts.get("baseUrl", ".")
            out = []
            for pat, targets in (opts.get("paths") or {}).items():
                for t in targets[:1]:
                    out.append((pat, os.path.normpath(os.path.join(base, t))))
            return out
        return []

    def unit(self, f: str) -> str:
        return (os.path.dirname(f) or ".") + "/" if f.endswith(".go") else f

    def resolve(self, f: str, target: str, level: int, names: str):
        if f.endswith((".py", ".pyi")):
            return self._py(f, target, level, names)
        if f.endswith(".go"):
            if self.go_module and (target == self.go_module or target.startswith(self.go_module + "/")):
                d = target[len(self.go_module):].strip("/") or "."
                return d + "/" if d in self.go_dirs else None
            return None
        return self._ts(f, target)

    def _py(self, f, target, level, names):
        if level:
            pkg = _py_module(f).split(".")
            if not f.endswith("__init__.py"):
                pkg = pkg[:-1]
            pkg = pkg[:len(pkg) - (level - 1)] if level > 1 else pkg
            base = ".".join(pkg + ([target] if target else []))
        else:
            base = target
        for n in (names or "").split(","):
            if n and f"{base}.{n}" in self.py_index:
                return self.py_index[f"{base}.{n}"]
        parts = base.split(".")
        while parts:
            mod = ".".join(parts)
            if mod in self.py_index:
                return self.py_index[mod]
            parts.pop()
        return None

    def _ts(self, f, target):
        cands = []
        if target.startswith("."):
            cands.append(os.path.normpath(os.path.join(os.path.dirname(f), target)))
        else:
            for pat, dest in self.ts_paths:
                if pat.endswith("*") and target.startswith(pat[:-1]):
                    cands.append(os.path.normpath(dest.replace("*", target[len(pat) - 1:])))
                elif pat == target:
                    cands.append(dest)
            if target.startswith("@/") or target.startswith("~/"):
                cands.append(os.path.normpath("src/" + target[2:]))
            for name, d in self.ts_packages:  # the repo's own package name / workspace packages
                if target == name or target.startswith(name + "/"):
                    sub = target[len(name):].lstrip("/")
                    if sub:
                        cands += [os.path.join(d, sub), os.path.join(d, "src", sub)]
                    else:
                        cands += [os.path.join(d, "src", "index"), os.path.join(d, "index"), os.path.join(d, "src", "main"),
                                  os.path.join(d, "src", Path(name).name)]
                    break
        for c in cands:
            c = os.path.normpath(c)
            c = c[2:] if c.startswith("./") else c
            for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", "/index.ts", "/index.tsx",
                        "/index.js", "/index.jsx"):
                if c + ext in self.files:
                    return c + ext
            if c.endswith(".js") and c[:-3] + ".ts" in self.files:  # ESM-style ".js" import of a .ts file
                return c[:-3] + ".ts"
        return None


# ---------------------------------------------------------------------------
# build


def build(root: str, quiet: bool = True, full: bool = False) -> dict:
    """Parse new/changed files and refresh the graph. Returns build stats."""
    root = str(Path(root).resolve())
    t0 = time.time()
    listed = outline.list_files(root)
    all_files = [f for f in listed if Path(f).suffix in outline.SOURCE_EXT]
    gen_re = langs.generated_re(list(langs.PROFILES))
    resolver = Resolver(root, all_files, listed)
    parsed = skipped = errors = 0
    with connect(root) as db:
        if full:
            for t in ("files", "symbols", "refs", "imports", "idents"):
                db.execute(f"DELETE FROM {t}")
        known = {r[0]: (r[1], r[2]) for r in db.execute("SELECT path, mtime_ns, size FROM files")}
        current = set(all_files)
        for gone in set(known) - current:
            _forget(db, gone)
        for f in all_files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if known.get(f) == (st.st_mtime_ns, st.st_size):
                skipped += 1
                continue
            _forget(db, f)
            lang = LANG_OF.get(Path(f).suffix, "other")
            try:
                src = Path(p).read_text(errors="replace") if st.st_size <= MAX_FILE_BYTES else ""
            except OSError:
                continue
            syms, refs, imps = [], [], []
            if src:
                try:
                    if lang == "python":
                        syms, refs, imps = parse_python(f, src)
                    elif lang == "go":
                        syms, refs, imps = parse_go(f, src)
                    elif lang == "ts":
                        syms, refs, imps = parse_ts(f, src)
                    else:
                        syms = [(_sym_name(sig) or sig[:40], "symbol", "", s, e, sig, "", 1)
                                for s, e, d, sig in outline.outline(f, src) if d == 0]
                except (SyntaxError, ValueError, RecursionError):
                    errors += 1
                    syms = [(_sym_name(sig) or sig[:40], "symbol", "", s, e, sig, "", 1)
                            for s, e, d, sig in outline.outline(f, src) if d <= 1]
            db.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?)",
                       (f, lang, resolver.unit(f), st.st_mtime_ns, st.st_size, src.count("\n") + 1 if src else 0,
                        int(bool(TEST_FILE.search(f))), int(bool(gen_re and gen_re.search(f)))))
            db.executemany("INSERT INTO symbols (file, name, kind, parent, start, end, signature, doc, exported) "
                           "VALUES (?,?,?,?,?,?,?,?,?)", [(f, *s) for s in syms])
            db.executemany("INSERT INTO refs VALUES (?,?,?,?,?)", [(f, *r) for r in refs])
            db.executemany("INSERT INTO imports VALUES (?,?,?,?,?)",
                           [(f, t, resolver.resolve(f, t, lvl, names), names, tonly) for t, lvl, names, tonly in imps])
            db.executemany("INSERT INTO idents VALUES (?,?,?)", [(f, n, c) for n, c in IDENTS.pop(f, {}).items()])
            parsed += 1
        stats = {"files": len(all_files), "parsed": parsed, "unchanged": skipped, "errors": errors,
                 "seconds": round(time.time() - t0, 2), "built": time.time()}
        db.execute("INSERT OR REPLACE INTO meta VALUES ('built', ?)", (json.dumps(stats),))
        db.execute("INSERT OR REPLACE INTO meta VALUES ('root', ?)", (root,))
    if not quiet:
        print(f"graph: {len(all_files)} files ({parsed} parsed, {skipped} unchanged) in {stats['seconds']}s "
              f"· {db_path(root)}")
    return stats


def _forget(db, f):
    for t, col in (("files", "path"), ("symbols", "file"), ("refs", "file"), ("imports", "file"), ("idents", "file")):
        db.execute(f"DELETE FROM {t} WHERE {col}=?", (f,))


def _sym_name(sig: str):
    return outline._name(sig)


# ---------------------------------------------------------------------------
# loading for queries


CALLABLE = {"function", "method", "component", "hook", "class", "struct"}
KIND_WEIGHT = {"function": 1.0, "method": 1.0, "component": 1.0, "hook": 1.0, "class": 1.0, "struct": 1.0,
               "interface": 0.8, "type": 0.7, "enum": 0.7, "constant": 0.5, "symbol": 0.6}


class Graph:
    """Read-only, in-memory view used by queries, the report and the dashboard."""

    def __init__(self, root: str):
        self.root = str(Path(root).resolve())
        with connect(self.root) as db:
            self.meta = json.loads((db.execute("SELECT value FROM meta WHERE key='built'").fetchone() or ["{}"])[0])
            self.files = {r[0]: {"lang": r[1], "unit": r[2], "lines": r[3], "test": bool(r[4]), "generated": bool(r[5])}
                          for r in db.execute("SELECT path, lang, unit, lines, is_test, is_generated FROM files")}
            self.symbols = [dict(zip(("id", "file", "name", "kind", "parent", "start", "end", "signature", "doc",
                                      "exported"), r))
                            for r in db.execute("SELECT id, file, name, kind, parent, start, end, signature, doc, "
                                                "exported FROM symbols")]
            self.refs = db.execute("SELECT file, scope, name, kind, line FROM refs").fetchall()
            self.imports = db.execute("SELECT file, target, resolved, names, type_only FROM imports").fetchall()
        self.by_name = defaultdict(list)
        self.by_file = defaultdict(list)
        for s in self.symbols:
            self.by_name[s["name"]].append(s)
            self.by_file[s["file"]].append(s)
        self.unit_files = defaultdict(list)
        for f, info in self.files.items():
            self.unit_files[info["unit"]].append(f)
        self.out_units = defaultdict(set)   # unit -> units it imports
        self.in_units = defaultdict(set)    # unit -> units importing it
        self.runtime_out = defaultdict(set)  # without type-only imports and package re-exports (for cycles)
        for f, _, resolved, _, type_only in self.imports:
            if resolved and f in self.files:
                src_u = self.files[f]["unit"]
                dst_u = resolved if resolved.endswith("/") else self.files.get(resolved, {}).get("unit", resolved)
                if dst_u != src_u:
                    self.out_units[src_u].add(dst_u)
                    self.in_units[dst_u].add(src_u)
                    if not type_only and not re.search(r"(^|/)(__init__\.pyi?|index\.[cm]?[jt]sx?)$", dst_u):
                        self.runtime_out[src_u].add(dst_u)
        self.ref_count = Counter()
        self.ref_files = defaultdict(set)
        for f, _, name, _, _ in self.refs:
            self.ref_count[name] += 1
            self.ref_files[name].add(f)
        self._rank = None

    # -- ranking -----------------------------------------------------------
    def rank(self):
        """PageRank over the unit import graph (units depended on by many rank high)."""
        if self._rank is None:
            units = set(self.unit_files) | set(self.in_units) | set(self.out_units)
            units = {u for u in units if u in self.unit_files}
            n = len(units) or 1
            pr = {u: 1 / n for u in units}
            for _ in range(30):
                nxt = {u: 0.15 / n for u in units}
                for u in units:
                    outs = [v for v in self.out_units.get(u, ()) if v in units]
                    if outs:
                        share = 0.85 * pr[u] / len(outs)
                        for v in outs:
                            nxt[v] += share
                    else:
                        for v in units:
                            nxt[v] += 0.85 * pr[u] / n
                pr = nxt
            self._rank = pr
        return self._rank

    def unit_of(self, f: str) -> str:
        return self.files.get(f, {}).get("unit", f)

    def is_test_unit(self, u: str) -> bool:
        return all(self.files[f]["test"] for f in self.unit_files.get(u, [])) if self.unit_files.get(u) else False

    def is_aux_unit(self, u: str) -> bool:
        """Examples, docs, benchmarks, scripts: real code, but not what a task is usually about."""
        return bool(AUX_FILE.search(u))

    def core_units(self):
        pr = self.rank()
        return [u for u in sorted(pr, key=lambda u: -pr[u]) if not self.is_test_unit(u) and not self.is_aux_unit(u)]

    # -- lookups ------------------------------------------------------------
    def find(self, target: str):
        """Resolve a user/agent target: a file path, a directory/package, Name or Parent.name."""
        t = target.strip().rstrip("/")
        if t in self.files:
            return "file", t
        if t + "/" in self.unit_files:
            return "unit", t + "/"
        ends = [f for f in self.files if f.endswith("/" + t) or f == t]
        if len(ends) == 1:
            return "file", ends[0]
        if "." in t and not t.endswith((".py", ".go", ".ts", ".tsx", ".js", ".jsx")):
            parent, name = t.rsplit(".", 1)
            hits = [s for s in self.by_name.get(name, []) if s["parent"].split(".")[-1] == parent.split(".")[-1]]
            if hits:
                return "symbol", hits
        hits = self.by_name.get(t)
        if hits:
            return "symbol", hits
        lower = [s for n, ss in self.by_name.items() if n.lower() == t.lower() for s in ss]
        if lower:
            return "symbol", lower
        return None, None

    def callers(self, name: str, limit: int = 40):
        out = []
        for f, scope, n, kind, line in self.refs:
            if n == name and kind in ("call", "render", "inherit", "decorate", "use"):
                out.append((f, line, scope or "<module>", kind))
        out.sort(key=lambda r: (self.files.get(r[0], {}).get("test", False), bool(AUX_FILE.search(r[0])), r[0], r[1]))
        return out[:limit], len(out)

    def callees(self, sym: dict, limit: int = 30):
        qual = f"{sym['parent']}.{sym['name']}" if sym["parent"] else sym["name"]
        unit = self.unit_of(sym["file"])
        allowed = {unit} | self.out_units.get(unit, set())
        names = Counter(n for f, scope, n, kind, line in self.refs
                        if f == sym["file"] and (scope == qual or scope.startswith(qual + ".")) and n != sym["name"]
                        and any(d["kind"] in CALLABLE and self.unit_of(d["file"]) in allowed
                                for d in self.by_name.get(n, ())))
        return [n for n, _ in names.most_common(limit)]

    def importers(self, unit: str):
        return sorted(self.in_units.get(unit, ()))

    def tests_for(self, units):
        """Test files that import one of `units` or reference their exported symbols."""
        units = set(units)
        out = set()
        for u in units:
            for v in self.in_units.get(u, ()):
                out.update(f for f in self.unit_files.get(v, ()) if self.files[f]["test"])
        names = {s["name"] for u in units for f in self.unit_files.get(u, ()) for s in self.by_file[f]
                 if s["exported"] and len(s["name"]) > 3}
        for name in names:
            for f in self.ref_files.get(name, ()):
                if self.files.get(f, {}).get("test"):
                    fu = self.unit_of(f)
                    if fu in units or units & self.out_units.get(fu, set()):
                        out.add(f)
        return sorted(f for f in out if not AUX_FILE.search(f))


# ---------------------------------------------------------------------------
# queries (text output for Claude, token-budgeted)


def _loc(s):
    return f"{s['file']}:{s['start']}" + (f"-{s['end']}" if s["end"] and s["end"] > s["start"] else "")


def _qual(s):
    return f"{s['parent']}.{s['name']}" if s["parent"] else s["name"]


def _fit(lines, budget: int):
    out, used = [], 0
    for ln in lines:
        cost = tokens.count(ln) + 1
        if used + cost > budget and out:
            out.append(f"… (cut to fit {budget} tokens; narrow the query or raise --budget)")
            break
        out.append(ln)
        used += cost
    return "\n".join(out)


def load(root: str, build_if_missing: bool = True) -> Graph:
    if not exists(root):
        if not build_if_missing:
            raise FileNotFoundError("no code graph yet; run `kompact graph build`")
        build(root)
    return Graph(root)


def query(root: str, text: str, budget: int = 1500) -> str:
    """Find the code most related to a free-text question, with its neighbourhood."""
    g = load(root)
    words = [w for w in split_words(text) if len(w) > 1 and w not in STOP]
    if not words:
        return "query: give some words, e.g. `kompact graph query \"session cookie signing\"`"
    df = Counter()
    sym_words = []
    for s in g.symbols:
        ws = set(split_words(s["name"])) | set(split_words(s["parent"]))
        ws |= {w for w in split_words(s["doc"]) if len(w) > 3}
        ws |= set(split_words(Path(s["file"]).stem))
        sym_words.append(ws)
        df.update(ws)
    n = len(g.symbols) or 1
    scored = []
    for s, ws in zip(g.symbols, sym_words):
        score = 0.0
        for w in words:
            if w in ws:
                idf = max(0.2, math.log(n / (1 + df[w])))
                score += idf * (2.0 if w in split_words(s["name"]) else 1.0)
        if score:
            score *= KIND_WEIGHT.get(s["kind"], 0.8)
            if g.files.get(s["file"], {}).get("test"):
                score *= 0.4
            elif AUX_FILE.search(s["file"]):
                score *= 0.6
            score *= 1 + min(g.ref_count.get(s["name"], 0), 50) / 50
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return f'query "{text}": no matching symbols. Try other words, or `kompact graph report` for an overview.'
    out = [f'query "{text}": {len(scored)} matches, best first']
    per_file, picked, more = Counter(), [], Counter()
    for score, s in scored:
        if per_file[s["file"]] >= 4:
            more[s["file"]] += 1
            continue
        per_file[s["file"]] += 1
        picked.append((score, s))
        if len(picked) >= 12:
            break
    for i, (score, s) in enumerate(picked, 1):
        out.append(f"{i}. {_loc(s)}  {s['kind']} {_qual(s)}" + (f" — {s['doc']}" if s["doc"] else ""))
        out.append(f"   {s['signature']}")
        callers, total = g.callers(s["name"], limit=5)
        if callers and s["kind"] not in ("constant",):
            shown = ", ".join(f"{c[0]}:{c[1]}" for c in callers[:4])
            out.append(f"   used by: {shown}" + (f" (+{total - 4})" if total > 4 else ""))
        calls = g.callees(s, limit=6) if s["kind"] in ("function", "method", "component", "hook") else []
        if calls:
            out.append(f"   calls: {', '.join(calls)}")
    if more:
        out.append("more matches in: " + ", ".join(f"{f} (+{n})" for f, n in more.most_common(5)))
    return _fit(out, budget)


STOP = {"the", "a", "an", "of", "to", "in", "and", "or", "for", "is", "how", "where", "what", "which", "does", "do",
        "with", "on", "by", "from", "it", "this", "that", "are", "be", "when", "why", "who", "find", "code", "file"}


def callers_text(root: str, name: str, budget: int = 1200) -> str:
    g = load(root)
    kind, hits = g.find(name)
    leaf = name.split(".")[-1]
    defs = hits if kind == "symbol" else []
    rows, total = g.callers(leaf, limit=200)
    out = [f"{name}: defined at " + (", ".join(_loc(s) for s in defs[:5]) if defs else "(not found in this repo)"),
           f"referenced {total}× in {len({r[0] for r in rows})} files" + (" (by name; may include same-named symbols)"
                                                                           if len(defs) > 1 else "")]
    for f, line, scope, k in rows:
        out.append(f"  {f}:{line}  {scope}" + ("" if k == "call" else f"  [{k}]"))
    return _fit(out, budget)


def deps_text(root: str, target: str, budget: int = 1200) -> str:
    g = load(root)
    kind, val = g.find(target)
    if kind is None:
        return f"{target}: not found (give a file path, package dir, Name or Class.method)"
    if kind == "symbol":
        out = []
        for s in val[:3]:
            calls = g.callees(s, limit=40)
            out.append(f"{_qual(s)} ({_loc(s)}) uses:")
            for c in calls:
                d = g.by_name.get(c, [])
                out.append(f"  {c}  " + (", ".join(_loc(x) for x in d[:2]) if d else ""))
        return _fit(out, budget)
    unit = g.unit_of(val) if kind == "file" else val
    outs = sorted(g.out_units.get(unit, ()))
    ext = sorted({t for f, t, r, _, _ in g.imports if g.unit_of(f) == unit and not r})
    out = [f"{unit} imports {len(outs)} project modules:"] + [f"  {u}" for u in outs]
    if ext:
        out.append(f"external: {', '.join(ext[:30])}" + (" …" if len(ext) > 30 else ""))
    return _fit(out, budget)


def impact(root: str, target: str, depth: int = 3):
    """What may break if `target` (file, package dir, or symbol) changes.

    Direct users are files that reference the target's symbols and can see them
    (same module/package, or importing it). Indirect users follow the import graph.
    Tests are test files that reference the symbols or import an affected module."""
    g = load(root)
    kind, val = g.find(target)
    if kind is None:
        return None, g
    if kind == "symbol":
        files = {s["file"] for s in val}
        names = {s["name"] for s in val}
    else:
        files = {val} if kind == "file" else set(g.unit_files.get(val, []))
        names = {s["name"] for f in files for s in g.by_file[f] if s["exported"] and len(s["name"]) > 3}
    start = {g.unit_of(f) for f in files}
    direct = set()
    for n in names:
        for f in g.ref_files.get(n, ()):
            if f in files:
                continue
            u = g.unit_of(f)
            if u in start or start & g.out_units.get(u, set()):
                direct.add(f)
    for u in start:  # importers count as direct users even without a resolved symbol reference
        for v in g.in_units.get(u, ()):
            direct.update(g.unit_files.get(v, ()))
    tests = sorted(f for f in direct if g.files[f]["test"] and not AUX_FILE.search(f))
    direct_code = sorted(f for f in direct if not g.files[f]["test"])
    levels = [direct_code] if direct_code else []
    seen = start | {g.unit_of(f) for f in direct}
    frontier = {g.unit_of(f) for f in direct_code}
    for _ in range(depth - 1):
        nxt = set()
        for u in frontier:
            nxt |= g.in_units.get(u, set())
        nxt -= seen
        if not nxt:
            break
        seen |= nxt
        code = sorted(f for v in nxt for f in g.unit_files.get(v, ()) if not g.files[f]["test"])
        tests += [f for v in nxt for f in g.unit_files.get(v, ()) if g.files[f]["test"] and not AUX_FILE.search(f)]
        if code:
            levels.append(code)
        frontier = nxt
    affected = sorted({f for lvl in levels for f in lvl})
    return {"target": target, "files": sorted(files), "levels": levels, "affected": affected,
            "tests": sorted(set(tests))}, g


def impact_text(root: str, target: str, budget: int = 1200) -> str:
    res, g = impact(root, target)
    if res is None:
        return f"{target}: not found (give a file path, package dir, Name or Class.method)"
    aux = [f for f in res["affected"] if AUX_FILE.search(f)]
    out = [f"impact of {target}: {len(res['affected']) - len(aux)} dependent files, {len(res['tests'])} test files"
           + (f", {len(aux)} in examples/tooling" if aux else "")]
    for i, lvl in enumerate(res["levels"], 1):
        code = [f for f in lvl if not AUX_FILE.search(f)]
        if code:
            out.append(f"  {'direct' if i == 1 else f'{i} hops'}: " + ", ".join(code[:25]) + (" …" if len(code) > 25 else ""))
    if res["tests"]:
        out.append("  tests to run: " + ", ".join(res["tests"][:20]) + (" …" if len(res["tests"]) > 20 else ""))
    return _fit(out, budget)


def path_text(root: str, a: str, b: str) -> str:
    g = load(root)
    ka, va = g.find(a)
    kb, vb = g.find(b)
    if not ka or not kb:
        return f"not found: {a if not ka else b}"
    ua = {g.unit_of(s["file"]) for s in va} if ka == "symbol" else {g.unit_of(va) if ka == "file" else va}
    ub = {g.unit_of(s["file"]) for s in vb} if kb == "symbol" else {g.unit_of(vb) if kb == "file" else vb}
    for direction, adj in (("imports", g.out_units), ("is imported by", g.in_units)):
        prev = {u: None for u in ua}
        q = deque(ua)
        while q:
            u = q.popleft()
            if u in ub:
                chain = []
                while u is not None:
                    chain.append(u)
                    u = prev[u]
                chain.reverse()
                return f"{a} {direction} {b} via {len(chain) - 1} step(s):\n  " + "\n  › ".join(chain)
            for v in adj.get(u, ()):
                if v not in prev:
                    prev[v] = u
                    q.append(v)
    return f"no import path between {a} and {b}"


# ---------------------------------------------------------------------------
# report & map


def areas(g: Graph, max_areas: int = 12):
    """Group units into areas by directory, then merge tiny areas into their parent."""
    by_dir = defaultdict(list)
    for u in g.unit_files:
        d = u.rstrip("/") if u.endswith("/") else os.path.dirname(u)
        by_dir[d or "."].append(u)
    return sorted(by_dir.items(), key=lambda kv: -sum(g.rank().get(u, 0) for u in kv[1]))[:max_areas]


def _key_symbols(g: Graph, u: str):
    seen, out = set(), []
    syms = [s for f in g.unit_files[u] for s in g.by_file[f] if s["exported"]
            and s["kind"] not in ("constant", "method", "symbol")]
    syms.sort(key=lambda s: -g.ref_count.get(s["name"], 0))
    for s in syms:
        if s["name"] not in seen and s["name"] not in ("wrapper", "decorator", "inner"):
            seen.add(s["name"])
            out.append(s["name"])
    return out


def import_cycles(g: Graph, limit: int = 8):
    """Strongly connected groups of modules that import each other (Tarjan)."""
    index, low, stack, on, out = {}, {}, [], set(), []
    counter = [0]

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in g.runtime_out.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 10000))
    try:
        for v in list(g.runtime_out):
            if v not in index:
                strong(v)
    finally:
        sys.setrecursionlimit(old)
    out.sort(key=len)
    return out[:limit]


IMPLICIT_METHODS = {
    # called by the runtime or a framework, not by name in the repo
    "String", "Error", "ServeHTTP", "Read", "Write", "Close", "Len", "Less", "Swap", "MarshalJSON", "UnmarshalJSON",
    "MarshalText", "UnmarshalText", "Format", "Unwrap", "Is", "As", "Scan", "Value", "init", "main", "TestMain",
    "setUp", "tearDown", "setUpClass", "tearDownClass", "asyncSetUp", "asyncTearDown", "run", "handle", "get", "post",
    "put", "patch", "delete", "dispatch", "render", "componentDidMount", "componentDidUpdate", "componentWillUnmount",
    "getDerivedStateFromProps", "shouldComponentUpdate", "constructor", "toString", "toJSON", "default", "handler",
    "middleware", "loader", "action", "generateMetadata", "generateStaticParams", "getServerSideProps",
    "getStaticProps", "getStaticPaths",
}
ROUTE_FILE = re.compile(r"(^|/)(pages|app)/.*\.(tsx?|jsx?)$|(^|/)(page|layout|route|loading|error|middleware)\.(tsx?|jsx?)$|"
                        r"(^|/)(manage|wsgi|asgi|conftest|setup|__main__)\.py$|(^|/)migrations/")


def unused(root: str):
    """Symbols whose name appears nowhere else in the repo. Returns (likely_dead, maybe_public)."""
    g = load(root)
    with connect(g.root) as db:
        totals = dict(db.execute("SELECT name, SUM(count) FROM idents GROUP BY name"))
    defs = Counter(s["name"] for s in g.symbols)
    dead, public = [], []
    for s in g.symbols:
        f, n = s["file"], s["name"]
        info = g.files.get(f, {})
        if info.get("lang") not in ("python", "go", "ts") or info.get("test") or info.get("generated") \
                or AUX_FILE.search(f) or ROUTE_FILE.search(f):
            continue
        if n.startswith("__") or n in IMPLICIT_METHODS or re.match(r"(test|Test|Benchmark|Example|Fuzz)", n):
            continue
        if s["signature"].startswith("@"):  # decorated: registered with a framework (routes, fixtures, CLI)
            continue
        if s["kind"] == "method" and defs[n] > 1:  # an override / interface implementation
            continue
        if totals.get(n, 0) > defs[n]:  # used somewhere besides its own definition(s)
            continue
        (public if s["exported"] else dead).append(s)
    key = lambda s: (s["file"], s["start"])  # noqa: E731
    return sorted(dead, key=key), sorted(public, key=key)


def unused_text(root: str, budget: int = 1500) -> str:
    dead, public = unused(root)
    if not dead and not public:
        return "No unused functions, classes or methods found."
    out = [f"Unused code candidates: {len(dead)} likely dead, {len(public)} exported but unreferenced"]
    if dead:
        out.append("likely dead (private or local; nothing references the name):")
        out += [f"  {_loc(s)}  {s['kind']} {_qual(s)}" for s in dead]
    if public:
        out.append("exported but unreferenced in this repo (may be public API):")
        out += [f"  {_loc(s)}  {s['kind']} {_qual(s)}" for s in public]
    out.append("Check before deleting: dynamic calls, reflection and external users are not visible to the graph.")
    return _fit(out, budget)


DEBT = re.compile(r"(?:(?:^|\s)(?:#|//|/\*+|<!--)|^\s*\*)\s*(shortcut|FIXME|BUG|HACK|XXX|TODO)\b[\s:(\-]*(.*)", re.I)


def debt_text(root: str, budget: int = 1500) -> str:
    """Ledger of shortcut:/FIXME/HACK/TODO comments, most serious first."""
    order = {"bug": 0, "fixme": 1, "hack": 2, "xxx": 3, "shortcut": 4, "todo": 5}
    rows = []
    for f in outline.list_files(root):
        if Path(f).suffix not in outline.SOURCE_EXT or AUX_FILE.search(f):
            continue
        try:
            text = Path(root, f).read_text(errors="replace") if os.path.getsize(Path(root, f)) < MAX_FILE_BYTES else ""
        except OSError:
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            m = DEBT.search(ln)
            if m:
                rows.append((order.get(m.group(1).lower(), 9), m.group(1).upper(), f, i, m.group(2).strip()[:140]))
    if not rows:
        return "No shortcut:, TODO, FIXME, HACK or XXX comments found."
    rows.sort()
    counts = Counter(r[1] for r in rows)
    out = ["Debt ledger: " + ", ".join(f"{n} {k}" for k, n in counts.most_common())]
    out += [f"  {tag:<8} {f}:{line}  {text}" for _, tag, f, line, text in rows]
    return _fit(out, budget)


def explain_text(root: str, name: str, budget: int = 1200) -> str:
    """Everything about one symbol: where, what, who uses it, what it uses, its tests."""
    g = load(root)
    kind, val = g.find(name)
    if kind != "symbol":
        return deps_text(root, name, budget) if kind else f"{name}: not found"
    out = []
    for s in val[:3]:
        out.append(f"{_qual(s)} — {s['kind']} at {_loc(s)}" + (f": {s['doc']}" if s["doc"] else ""))
        out.append(f"  {s['signature']}")
        rows, total = g.callers(s["name"], limit=8)
        if rows:
            out.append(f"  used by ({total}): " + ", ".join(f"{r[0]}:{r[1]} {r[2]}" for r in rows[:8]))
        calls = g.callees(s, limit=12)
        if calls:
            out.append("  uses: " + ", ".join(calls))
        tests = sorted({r[0] for r in g.callers(s["name"], limit=500)[0] if g.files.get(r[0], {}).get("test")})
        if tests:
            out.append("  tested in: " + ", ".join(tests[:6]))
    return _fit(out, budget)


def _is_reexport(g: Graph, u: str) -> bool:
    return bool(re.search(r"(^|/)(__init__\.pyi?|index\.[cm]?[jt]sx?|mod\.rs)$", u)) and bool(g.out_units.get(u))


def _key_files(g: Graph, n: int):
    score = Counter()
    for f, syms in g.by_file.items():
        if g.files.get(f, {}).get("test") or AUX_FILE.search(f):
            continue
        score[f] = sum(g.ref_count.get(s["name"], 0) for s in syms if s["exported"])
    out = []
    for f, _ in score.most_common(n):
        names = list(dict.fromkeys(s["name"] for s in sorted(g.by_file[f], key=lambda s: -g.ref_count.get(s["name"], 0))
                                   if s["exported"] and s["kind"] != "constant"))
        out.append((f, names))
    return out


def report(root: str, budget: int = 1800) -> str:
    g = load(root)
    pr = g.rank()
    langs_count = Counter(info["lang"] for info in g.files.values())
    m = g.meta
    out = [f"# Code graph: {Path(g.root).name}",
           f"{len(g.files)} files ({', '.join(f'{k} {v}' for k, v in langs_count.most_common())}) · "
           f"{len(g.symbols)} symbols · {len(g.refs)} references · {sum(len(v) for v in g.out_units.values())} "
           f"module imports · built in {m.get('seconds', '?')}s"]
    core = g.core_units()[:10]
    out.append("\n## Core modules (most depended on)")
    for u in core:
        syms = _key_symbols(g, u)
        if not syms and not _is_reexport(g, u):
            continue
        out.append(f"- {u} — imported by {len(g.in_units.get(u, ()))}; "
                   + ("key: " + ", ".join(syms[:6]) if syms else "re-exports"))
    if len(core) <= 3:  # one or few packages (typical Go): rank files instead
        out.append("\n## Key files")
        for f, names in _key_files(g, 8):
            out.append(f"- {f} — " + ", ".join(names[:8]))
    hubs = [(n, c) for n, c in g.ref_count.most_common(200) if n in g.by_name and len(n) > 2
            and any(not g.files.get(s["file"], {}).get("test") for s in g.by_name[n])][:12]
    out.append("\n## Most used symbols")
    out.append(", ".join(f"{n} ({c}× in {len(g.ref_files[n])} files)" for n, c in hubs))
    entry = [s for s in g.symbols if s["name"] in ("main", "cli", "run", "app", "App", "create_app", "Execute", "handler")
             and not g.files.get(s["file"], {}).get("test")]
    if entry:
        out.append("\n## Entry points")
        out.append(", ".join(f"{_qual(s)} ({_loc(s)})" for s in entry[:8]))
    out.append("\n## Areas")
    for d, units in areas(g):
        tests = sum(1 for u in units if g.is_test_unit(u))
        label = "tests" if tests == len(units) else "examples/docs/tooling" if g.is_aux_unit(d + "/") else ""
        out.append(f"- {d}/ — {len(units)} modules" + (f" ({label})" if label else f" ({tests} test)" if tests else ""))
    cycles = import_cycles(g)
    if cycles:
        out.append("\n## Import cycles (runtime imports only)")
        for c in cycles:
            out.append("- " + (" ⇄ ".join(c) if len(c) <= 4 else f"tangle of {len(c)}: " + ", ".join(c[:5]) + " …"))
    tested = defaultdict(set)
    for u in g.unit_files:
        if g.is_test_unit(u):
            for v in g.out_units.get(u, ()):
                if not g.is_test_unit(v) and not g.is_aux_unit(v):
                    tested[v].add(u)
    if tested:
        out.append("\n## Tests by module")
        for v in sorted(tested, key=lambda v: -pr.get(v, 0))[:10]:
            out.append(f"- {v} ← {', '.join(sorted(tested[v])[:4])}")
    out.append("\n## Next steps\n`kompact graph query \"<words>\"` · `kompact graph impact <file|symbol>` · "
               "`kompact graph callers <Name>` · `kompact symbol <Name>`")
    return _fit(out, budget)


def session_map(root: str, budget: int = 600) -> str:
    """Compact orientation map for SessionStart: top modules and their key symbols."""
    g = load(root, build_if_missing=False)
    lines = [f"[kompact] Code map of {Path(g.root).name} (most depended-on modules first; "
             f"`kompact graph query \"words\"` finds code by topic):"]
    core = g.core_units()
    if len(core) <= 3:  # one big package (typical Go): list key files instead
        for f, names in _key_files(g, 15):
            lines.append(f"{f}: {', '.join(names[:8])}")
    else:
        for u in core:
            syms = _key_symbols(g, u)
            if syms:
                lines.append(f"{u}: " + ", ".join(syms[:8]))
            elif _is_reexport(g, u):
                lines.append(f"{u}: (re-exports)")
    return _fit(lines, budget)


def file_context(root: str, path: str) -> str:
    """One or two lines placed under an outline: who imports this file and its tests."""
    if not exists(root):
        return ""
    g = Graph(root)
    rel = os.path.relpath(path, g.root) if os.path.isabs(path) else path
    if rel not in g.files:
        return ""
    u = g.unit_of(rel)
    imp = [v for v in g.importers(u) if not g.is_test_unit(v)]
    tests = g.tests_for({u})
    parts = []
    if imp:
        parts.append("imported by " + ", ".join(imp[:6]) + (f" (+{len(imp) - 6})" if len(imp) > 6 else ""))
    if tests:
        parts.append("tests: " + ", ".join(tests[:4]) + (f" (+{len(tests) - 4})" if len(tests) > 4 else ""))
    return "Graph: " + "; ".join(parts) if parts else ""


def viz(root: str, limit: int = 60) -> dict:
    """Nodes and edges of the top units for the dashboard's graph view: the most
    central code modules, plus the most central tests/examples flagged `aux`."""
    g = load(root, build_if_missing=False)
    pr = g.rank()
    ranked = sorted(pr, key=lambda u: -pr[u])
    code = [u for u in ranked if not g.is_test_unit(u) and not g.is_aux_unit(u)][:limit]
    aux = [u for u in ranked if g.is_test_unit(u) or g.is_aux_unit(u)][:max(10, limit // 2)]
    top = code + aux
    keep = set(top)
    nodes = [{"id": u, "rank": round(pr[u], 5), "test": g.is_test_unit(u), "aux": g.is_test_unit(u) or g.is_aux_unit(u),
              "in": len(g.in_units.get(u, ())),
              "out": len(g.out_units.get(u, ())), "lang": g.files[g.unit_files[u][0]]["lang"] if g.unit_files[u] else "",
              "lines": sum(g.files[f]["lines"] for f in g.unit_files[u]),
              "symbols": [_qual(s) for f in g.unit_files[u] for s in g.by_file[f] if s["exported"]
                          and s["kind"] not in ("constant",)][:12]} for u in top]
    edges = [{"source": u, "target": v} for u in top for v in g.out_units.get(u, ()) if v in keep]
    total_tokens = sum(g.files[f]["lines"] for f in g.files) * 9  # ~9 tokens per source line
    return {"nodes": nodes, "edges": edges, "meta": g.meta, "files": len(g.files), "symbols": len(g.symbols),
            "refs": len(g.refs), "units": len(g.unit_files), "approx_source_tokens": total_tokens,
            "map_tokens": tokens.count(session_map(root, 800)) if g.unit_files else 0}


def build_in_background(root: str) -> None:
    """Refresh the graph without blocking the hook that asked for it."""
    import subprocess
    import sys
    launch = Path(__file__).with_name("_launch.py")
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
              "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(launch), "graph", "build", "--root", root], **kwargs)


def ensure(root: str, sync_limit: int = 1500, max_age: float = 60) -> bool:
    """Make sure a reasonably fresh graph exists. Small repos build inline (well under a
    second); big ones and refreshes happen in the background. Returns True if a graph exists."""
    if exists(root):
        with connect(root) as db:
            built = json.loads((db.execute("SELECT value FROM meta WHERE key='built'").fetchone() or ["{}"])[0])
        if time.time() - built.get("built", 0) > max_age:
            build_in_background(root)
        return True
    if len(outline.list_files(root)) <= sync_limit:
        build(root)
        return True
    build_in_background(root)
    return False
