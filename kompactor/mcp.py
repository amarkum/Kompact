"""MCP server for the code graph: `kompactor mcp`.

Speaks the Model Context Protocol over stdio (newline-delimited JSON-RPC 2.0), so any MCP client (Claude Code,
Cursor, Codex, Gemini CLI, Windsurf, ...) can find code, callers, the impact of a change and outlines without
reading whole files. Stdlib only, like the rest of Kompactor. The graph is refreshed incrementally before each
answer, so results match the files on disk.

    claude mcp add kompactor -- kompactor mcp
"""

import contextlib
import json
import os
import sys
import time

from . import __version__, config, graph, outline

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
FRESH_SECONDS = 5  # rebuild (incrementally) when the graph is older than this

_NAME = {"type": "string", "description": "A symbol name (function, class, method as Class.method) or a file path."}
TOOLS = [
    ("graph_query", "Find code by topic: the files and symbols that best match some words, with their line ranges. "
                    "Use before searching or reading files.",
     {"query": {"type": "string", "description": "Words, a file or a symbol, e.g. 'session cookie refresh'."}},
     ["query"], lambda root, a: graph.query(root, a["query"], _budget(a, 1500))),
    ("graph_callers", "Who calls or uses a symbol, grouped by file, with the calling function.",
     {"name": _NAME}, ["name"], lambda root, a: graph.callers_text(root, a["name"], _budget(a, 1200))),
    ("graph_impact", "What a change to a file or symbol affects: the files that depend on it, directly and further "
                     "out, and the tests to run.",
     {"target": _NAME}, ["target"], lambda root, a: graph.impact_text(root, a["target"], _budget(a, 1200))),
    ("graph_deps", "What a file or module depends on (its imports, resolved to files) and what depends on it.",
     {"target": _NAME}, ["target"], lambda root, a: graph.deps_text(root, a["target"], _budget(a, 1200))),
    ("graph_explain", "One symbol in context: where it is defined, its signature and doc, who uses it, what it "
                      "calls and which tests cover it.",
     {"name": _NAME}, ["name"], lambda root, a: graph.explain_text(root, a["name"], _budget(a, 1200))),
    ("graph_path", "How one file or symbol connects to another through imports.",
     {"from": _NAME, "to": _NAME}, ["from", "to"], lambda root, a: graph.path_text(root, a["from"], a["to"])),
    ("graph_report", "An overview of the codebase: core modules, most-used symbols, entry points, areas, import "
                     "cycles and which tests cover which modules.",
     {}, [], lambda root, a: graph.report(root, _budget(a, 1800))),
    ("graph_unused", "Symbols nothing uses: likely dead code first, then public ones that may be used from outside.",
     {}, [], lambda root, a: graph.unused_text(root, _budget(a, 1500))),
    ("outline", "A file's structure (classes, functions, methods) with line ranges, instead of the whole file. Read "
                "just the ranges you need afterwards.",
     {"path": {"type": "string", "description": "File path, relative to the project or absolute."}}, ["path"],
     lambda root, a: outline.render_outline(_path(root, a["path"]))),
    ("symbol", "The source code of one definition (Name or Class.method), without reading the rest of the file.",
     {"name": {"type": "string", "description": "Function, class or Class.method."}}, ["name"],
     lambda root, a: _symbol(root, a["name"])),
]


def _budget(args: dict, default: int) -> int:
    try:
        return max(200, min(8000, int(args.get("budget") or default)))
    except (TypeError, ValueError):
        return default


def _path(root: str, p: str) -> str:
    full = os.path.realpath(p if os.path.isabs(p) else os.path.join(root, p))
    if not (full == root or full.startswith(root + os.sep)):
        raise ValueError("path is outside the project")
    if not os.path.isfile(full):
        raise ValueError(f"no such file: {p}")
    return full


def _symbol(root: str, name: str) -> str:
    hits = outline.find_symbol(name, root)
    if not hits:
        return f"no definition found for {name}"
    return "\n".join(f"── {os.path.relpath(f, root) if os.path.isabs(f) else f}:{s}-{e}\n{src}" for f, s, e, src in hits)


def tool_list() -> list:
    out = []
    for name, desc, props, required, _ in TOOLS:
        schema = {"type": "object", "properties": dict(props), "required": list(required)}
        if name.startswith("graph_") or name in ("outline", "symbol"):
            schema["properties"]["root"] = {"type": "string", "description": "Project folder (default: the folder "
                                                                             "the server was started in)."}
        if name.startswith("graph_") and name != "graph_path":
            schema["properties"]["budget"] = {"type": "integer", "description": "Max tokens of output."}
        out.append({"name": name, "description": desc, "inputSchema": schema,
                    "annotations": {"readOnlyHint": True, "openWorldHint": False}})
    return out


class Server:
    def __init__(self, root: str):
        self.root = os.path.realpath(config.project_root(root) or root)
        self.built = {}

    def _fresh(self, root: str) -> None:
        if time.time() - self.built.get(root, 0) > FRESH_SECONDS:
            graph.build(root)  # incremental: only new or changed files are parsed
            self.built[root] = time.time()

    def call(self, name: str, args: dict) -> dict:
        tool = next((t for t in TOOLS if t[0] == name), None)
        if tool is None:
            raise KeyError(name)
        root = os.path.realpath(config.project_root(args["root"]) or args["root"]) if args.get("root") else self.root
        missing = [r for r in tool[3] if not str(args.get(r) or "").strip()]
        if missing:
            return _text(f"missing argument: {', '.join(missing)}", error=True)
        try:
            with contextlib.redirect_stdout(sys.stderr):  # stdout carries the protocol; nothing else may print there
                if name.startswith("graph_"):
                    self._fresh(root)
                return _text(tool[4](root, args) or "nothing found")
        except (ValueError, FileNotFoundError, OSError) as e:
            return _text(str(e), error=True)

    def handle(self, msg: dict):
        """The response to one JSON-RPC message, or None for a notification."""
        mid, method, params = msg.get("id"), msg.get("method", ""), msg.get("params") or {}
        if mid is None:
            return None  # notifications (initialized, cancelled) need no answer
        try:
            if method == "initialize":
                asked = params.get("protocolVersion")
                result = {"protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                          "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": "kompactor", "title": "Kompactor code graph", "version": __version__},
                          "instructions": "Use graph_query to find code by topic, graph_explain or symbol for one "
                                          "definition, graph_callers and graph_impact before changing code, and "
                                          "outline instead of reading a whole large file."}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": tool_list()}
            elif method == "tools/call":
                try:
                    result = self.call(params.get("name", ""), params.get("arguments") or {})
                except KeyError:
                    return _error(mid, -32602, f"unknown tool: {params.get('name')}")
            elif method in ("resources/list", "prompts/list"):
                result = {method.split("/")[0]: []}
            else:
                return _error(mid, -32601, f"method not found: {method}")
        except Exception as e:  # never take the client down; report and keep serving
            return _error(mid, -32603, f"{type(e).__name__}: {e}")
        return {"jsonrpc": "2.0", "id": mid, "result": result}


def _text(text: str, error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def _error(mid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def serve(root: str = "", stdin=None, stdout=None) -> int:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    server = Server(root or os.getcwd())
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = _error(None, -32700, "parse error")
        else:
            batch = msg if isinstance(msg, list) else [msg]
            replies = [r for r in (server.handle(m) for m in batch if isinstance(m, dict)) if r]
            reply = replies if isinstance(msg, list) else (replies[0] if replies else None)
        if reply:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
    return 0
