"""Local settings & savings dashboard: `kompactor ui`.

Stdlib only. Binds to 127.0.0.1, checks the Host header (DNS rebinding) and a
per-launch token on every write (CSRF), so other websites can't change settings.
"""

import json
import os
import re
import secrets
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import difflib
import mimetypes

from . import __version__, config, estimate, filters, graph, installer, langs, store, tokens

TOKEN = secrets.token_urlsafe(24)
UI_FILE = Path(__file__).with_name("ui.html")
STATIC = Path(__file__).with_name("static")


# ---------------------------------------------------------------------------
# API


def preview(knobs: dict, languages, project: str = "", rows=None) -> list:
    """Your latest real command outputs (one project's, or every project's), or `rows`, as Claude would
    receive them under `knobs`."""
    out = []
    for s in (store.project_outputs(project) if rows is None else rows):
        cfg = dict(knobs, languages=languages)
        raw = tokens.count(s["text"])
        if not cfg.get("bash", True) or raw < cfg.get("bash_min_tokens", 0):
            text = s["text"]
        else:
            text = filters.compress(s["cmd"], s["text"], s.get("code", 0), stash_id=42, opts=cfg)
            if tokens.count(text) > raw * 0.9:
                text = s["text"]
        out.append({"id": s["id"], "label": s.get("label", s["cmd"]), "short": s.get("short", s["cmd"][:24]),
                    "lang": s.get("lang", ""), "project": s.get("project", ""),
                    "cmd": s["cmd"], "raw": raw,
                    "kept": tokens.count(text), "before": s["text"], "after": text,
                    "segments": segments(s["text"], text)})
    return out


def segments(before: str, after: str) -> list:
    """Line-level view of what was kept, dropped or added (notes) — for the preview."""
    a, b = filters.clean(before), after.split("\n")
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out += [["keep", ln] for ln in a[i1:i2]]
        else:
            out += [["drop", ln] for ln in a[i1:i2]]
            out += [["note", ln] for ln in b[j1:j2]]
    return out


def preset_savings(rows=None) -> dict:
    """% fewer tokens each level gives on your latest real command outputs (or `rows`); None before any are recorded."""
    rows = store.project_outputs("") if rows is None else rows
    res = {}
    for p, preset in config.PRESETS.items():
        out = preview({k: preset[k] for k in config.KNOBS}, [], rows=rows)
        r, k = sum(x["raw"] for x in out), sum(x["kept"] for x in out)
        res[p] = round(100 * (r - k) / r) if r else None
    return res


def state() -> dict:
    data = config.read_file()
    projects = list(dict.fromkeys(store.projects() + list(data["projects"])))
    cwd_project = config.project_root(os.getcwd())
    if cwd_project and (Path(cwd_project) / ".git").exists() and cwd_project not in projects:
        projects.append(cwd_project)
    return {
        "version": __version__,
        "config": data,
        "presets": {p: {"name": v["name"], "blurb": v["blurb"], **{k: v[k] for k in config.KNOBS}}
                    for p, v in config.PRESETS.items()},
        "preset_savings": preset_savings(),
        "knobs": {k: list(v) for k, v in config.KNOB_INFO.items()},
        "knob_order": config.KNOBS,
        "languages": {k: v["label"] for k, v in langs.PROFILES.items()},
        "projects": [{"path": p, "detected": langs.detect(p) if os.path.isdir(p) else [],
                      "override": data["projects"].get(p),
                      "team": config.team_settings(p) if os.path.isdir(p) else {}} for p in projects],
        "setup": installer.status(),
        "home": str(store.home()),
    }


def stats(params: dict) -> dict:
    days = float(params.get("days", ["30"])[0])
    project = params.get("project", [""])[0]
    since = time.time() - days * 86400
    where, args = "ts > ?", [since]
    if project:
        where += " AND project = ?"
        args.append(project)
    with store.connect() as db:
        tot = db.execute(f"SELECT COUNT(*), COALESCE(SUM(raw_tokens),0), COALESCE(SUM(kept_tokens),0) FROM events "
                         f"WHERE {where}", args).fetchone()
        feats = db.execute(f"SELECT feature, COUNT(*), SUM(raw_tokens), SUM(kept_tokens) FROM events WHERE {where} "
                           f"GROUP BY feature ORDER BY SUM(raw_tokens)-SUM(kept_tokens) DESC", args).fetchall()
        turns = db.execute(f"SELECT session, idx, ts, project, raw_tokens, kept_tokens, context_tokens, features "
                           f"FROM turns WHERE {where} ORDER BY ts DESC LIMIT 60", args).fetchall()
        top = db.execute(f"SELECT detail, COUNT(*), SUM(raw_tokens), SUM(kept_tokens) FROM events WHERE {where} "
                         f"AND feature='bash' GROUP BY detail ORDER BY SUM(raw_tokens)-SUM(kept_tokens) DESC LIMIT 10",
                         args).fetchall()
        sessions = db.execute(f"SELECT COUNT(DISTINCT session) FROM events WHERE {where}", args).fetchone()[0]
    return {
        "events": tot[0], "raw": tot[1], "kept": tot[2], "saved": tot[1] - tot[2], "sessions": sessions,
        "features": [{"feature": f[0], "count": f[1], "raw": f[2], "kept": f[3]} for f in feats],
        "turns": [{"session": t[0], "idx": t[1], "ts": t[2], "project": t[3], "raw": t[4], "kept": t[5],
                   "context": t[6], "features": json.loads(t[7] or "{}")} for t in reversed(turns)],
        "top": [{"cmd": t[0], "runs": t[1], "raw": t[2], "kept": t[3]} for t in top],
        "left": store.passes_page(days, project, int(params.get("left_page", ["0"])[0]),
                                  min(50, int(params.get("left_size", ["10"])[0]))),
        "live": store.read_live(),
    }


def graph_state(project: str) -> dict:
    if not project or not os.path.isdir(project):
        return {"exists": False}
    if not graph.exists(project):
        return {"exists": False, "project": project}
    v = graph.viz(project, 70)
    g = graph.Graph(project)
    dead, public = graph.unused(project)
    v.update(exists=True, project=project, cycles=len(graph.import_cycles(g)),
             unused={"dead": len(dead), "public": len(public)},
             hubs=[{"name": n, "refs": c, "files": len(g.ref_files[n])} for n, c in g.ref_count.most_common(300)
                   if n in g.by_name and len(n) > 2][:10],
             core=[{"unit": u, "importers": len(g.in_units.get(u, ())), "symbols": graph._key_symbols(g, u)[:6]}
                   for u in g.core_units()[:12]])
    return v


def save_config(body: dict) -> dict:
    data = config.read_file()
    if "preset" in body:
        p = int(body["preset"])
        if p not in config.PRESETS:
            raise ValueError("preset must be 1-5")
        data["preset"] = p
    if "overrides" in body:
        data["overrides"] = {k: config.coerce(k, v) for k, v in body["overrides"].items() if k in config.KNOBS}
    if "languages" in body:
        mode = body["languages"].get("mode", "auto")
        sel = [s for s in body["languages"].get("selected", []) if s in langs.PROFILES]
        data["languages"] = {"mode": "manual" if mode == "manual" else "auto", "selected": sel}
    if "general" in body:
        try:
            data["general"].update({k: config.coerce_general(k, v) for k, v in body["general"].items() if k in config.GENERAL})
        except re.error as e:
            raise ValueError(f"not a valid pattern: {e}")
    if "project" in body:
        path, ov = body["project"].get("path", ""), body["project"].get("override")
        if path:
            if ov:
                data["projects"][path] = {"preset": int(ov.get("preset", data["preset"])),
                                          "overrides": {k: config.coerce(k, v) for k, v in
                                                        ov.get("overrides", {}).items() if k in config.KNOBS}}
            else:
                data["projects"].pop(path, None)
    config.write_file(data)
    return {"ok": True, "config": data}


# ---------------------------------------------------------------------------
# HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = "kompactor"

    def log_message(self, *a):  # quiet
        pass

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code: int, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "bad host"})
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/index.html"):
                html = UI_FILE.read_text().replace("__KOMPACTOR_TOKEN__", TOKEN)
                return self._send(200, html.encode(), "text/html; charset=utf-8")
            if u.path == "/api/ping":
                return self._send(200, {"kompactor": __version__})
            if u.path == "/api/state":
                return self._send(200, state())
            if u.path == "/api/stats":
                return self._send(200, stats(parse_qs(u.query)))
            if u.path == "/api/turn":
                q = parse_qs(u.query)
                items = store.turn_outputs(q.get("session", [""])[0], int(q.get("idx", ["0"])[0]))
                for it in items:
                    it["segments"] = segments(it["before"], it["after"]) if it["before"] and it["after"] else []
                return self._send(200, {"items": items})
            if u.path == "/api/graph":
                return self._send(200, graph_state(parse_qs(u.query).get("project", [""])[0]))
            if u.path in ("/usage", "/usage.html", "/guide"):
                self.send_response(302)
                self.send_header("Location", "/static/usage.html")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            if u.path.startswith("/static/"):
                f = (STATIC / u.path[len("/static/"):]).resolve()
                if STATIC.resolve() in f.parents and f.is_file():
                    ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                    if f.suffix == ".woff2":
                        ctype = "font/woff2"
                    return self._send(200, f.read_bytes(), ctype)
                return self._send(404, {"error": "not found"})
            return self._send(404, {"error": "not found"})
        except Exception as e:  # pragma: no cover - surfaced in the UI
            return self._send(500, {"error": str(e)})

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Kompactor-Token") != TOKEN:
            return self._send(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            u = urlparse(self.path).path
            if u == "/api/config":
                return self._send(200, save_config(body))
            if u == "/api/preview":
                knobs = {k: config.coerce(k, v) for k, v in body.get("knobs", {}).items() if k in config.KNOBS}
                return self._send(200, {"outputs": preview(knobs, body.get("languages") or [],
                                                           str(body.get("project") or ""))})
            if u == "/api/setup":
                action = body.get("action")
                target = installer.install(statusline=bool(body.get("statusline", True)),
                                           uninstall=action == "uninstall")
                return self._send(200, {"ok": True, "file": str(target), "setup": installer.status()})
            if u == "/api/delete":
                since, until = float(body.get("since") or 0), float(body.get("until") or 0)
                if since < 0 or until < 0 or (until and until < since):
                    raise ValueError("pick a 'to' time after the 'from' time")
                return self._send(200, {"deleted": store.delete(str(body.get("project") or ""), since, until)})
            if u == "/api/selftest":
                return self._send(200, {"results": installer.selftest()})
            if u.startswith("/api/graph/"):
                project = body.get("project", "")
                if not project or not os.path.isdir(project):
                    raise ValueError("unknown project")
                action = u.rsplit("/", 1)[1]
                if action == "build":
                    graph.build(project)
                    return self._send(200, graph_state(project))
                text = {"query": lambda: graph.query(project, body.get("q", ""), 1800),
                        "report": lambda: graph.report(project, 2500),
                        "unused": lambda: graph.unused_text(project, 2500),
                        "debt": lambda: graph.debt_text(project, 2500),
                        "impact": lambda: graph.impact_text(project, body.get("q", ""), 1800),
                        "explain": lambda: graph.explain_text(project, body.get("q", ""), 1800)}.get(action)
                if not text:
                    return self._send(404, {"error": "not found"})
                return self._send(200, {"text": text()})
            if u == "/api/estimate":
                s = estimate.run(limit=int(body.get("limit") or 0) or None, style_pct=0)
                return self._send(200, {"sessions": s["sessions"], "calls": s["calls"],
                                        "tool_tokens": s["tool_tokens"], "saved_tool": s["saved_tool"],
                                        "billed": s["billed"], "saved_billed": s["saved_billed"],
                                        "cost": s["cost"], "saved_cost": s["saved_cost"],
                                        "by_feature": dict(s["by_feature"])})
            return self._send(404, {"error": "not found"})
        except (ValueError, KeyError, RuntimeError) as e:
            return self._send(400, {"error": str(e)})


def _free_port(preferred: int) -> int:
    for port in [preferred] + list(range(preferred + 1, preferred + 20)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


def serve(port: int = 7420, open_browser: bool = True, print_url: bool = True, exact: bool = False) -> None:
    port = port if exact else _free_port(port)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    if print_url:
        print(f"Kompactor dashboard: {url}  (Ctrl+C to stop)", flush=True)
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
