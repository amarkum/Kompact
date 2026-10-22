"""Local SQLite store: savings ledger, per-turn summaries, stashed raw outputs
(FTS5), and the Read tracker. Lives in ~/.kompactor (override with KOMPACTOR_HOME)."""

import bisect
import json
import os
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    ts REAL, session TEXT, feature TEXT, detail TEXT,
    raw_tokens INTEGER, kept_tokens INTEGER, project TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS stash (
    id INTEGER PRIMARY KEY, ts REAL, cmd TEXT, output TEXT, session TEXT DEFAULT '', project TEXT DEFAULT '',
    code INTEGER DEFAULT 0, shown TEXT
);
CREATE TABLE IF NOT EXISTS reads (
    session TEXT, path TEXT, sig TEXT, state TEXT, pending INTEGER DEFAULT 0, ts REAL,
    PRIMARY KEY (session, path)
);
CREATE TABLE IF NOT EXISTS sessions (
    session TEXT PRIMARY KEY, project TEXT, started REAL, last_turn REAL, compacted REAL DEFAULT 0,
    turns INTEGER DEFAULT 0, model TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS flags (
    session TEXT, key TEXT, ts REAL, PRIMARY KEY (session, key)
);
CREATE TABLE IF NOT EXISTS turns (
    session TEXT, idx INTEGER, ts REAL, project TEXT, raw_tokens INTEGER, kept_tokens INTEGER,
    context_tokens INTEGER, features TEXT
);
CREATE TABLE IF NOT EXISTS context (
    session TEXT PRIMARY KEY, tokens INTEGER, ts REAL
);
CREATE TABLE IF NOT EXISTS calls (
    session TEXT, ts REAL, kind TEXT
);
CREATE TABLE IF NOT EXISTS passes (
    ts REAL, session TEXT, project TEXT, tool TEXT, detail TEXT, tokens INTEGER, reason TEXT
);
"""


def home() -> Path:
    p = Path(os.environ.get("KOMPACTOR_HOME", Path.home() / ".kompactor"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def paused() -> bool:
    """`kompactor stop` leaves this marker; hooks and the shell prefix then pass everything through."""
    return (home() / "paused").exists()


class _Conn(sqlite3.Connection):
    """`with connect() as db:` commits (or rolls back) and then closes."""
    fts = False

    def __exit__(self, *exc):
        try:
            return super().__exit__(*exc)
        finally:
            self.close()


def connect() -> _Conn:
    db = sqlite3.connect(home() / "kompactor.db", timeout=10, factory=_Conn)
    db.execute("PRAGMA journal_mode=WAL")  # concurrent hooks + dashboard without lock errors
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript(SCHEMA)
    if "project" not in {r[1] for r in db.execute("PRAGMA table_info(events)")}:  # created by v0.1
        db.execute("ALTER TABLE events ADD COLUMN project TEXT DEFAULT ''")
    if "model" not in {r[1] for r in db.execute("PRAGMA table_info(sessions)")}:  # created before v0.8.5
        db.execute("ALTER TABLE sessions ADD COLUMN model TEXT DEFAULT ''")
    if "stash_id" not in {r[1] for r in db.execute("PRAGMA table_info(events)")}:  # created before v0.8.6
        db.execute("ALTER TABLE events ADD COLUMN stash_id INTEGER DEFAULT 0")
    have = {r[1] for r in db.execute("PRAGMA table_info(stash)")}
    for col, decl in (("session", "TEXT DEFAULT ''"), ("project", "TEXT DEFAULT ''"), ("code", "INTEGER DEFAULT 0"),
                      ("shown", "TEXT")):
        if col not in have:  # created before v0.8.6
            db.execute(f"ALTER TABLE stash ADD COLUMN {col} {decl}")
    db.execute("CREATE INDEX IF NOT EXISTS calls_session ON calls(session, ts)")
    db.execute("CREATE INDEX IF NOT EXISTS events_session ON events(session, ts)")
    db.execute("CREATE INDEX IF NOT EXISTS passes_ts ON passes(ts)")
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS stash_fts USING fts5(output, content='stash', content_rowid='id')")
        db.fts = True
    except sqlite3.OperationalError:  # sqlite built without FTS5
        db.fts = False
    return db


def record(feature: str, raw: int, kept: int, detail: str = "", session: str = "", force: bool = False,
           project: str = "", stash_id: int = 0) -> None:
    """Log a saving. `force` allows negative entries (reversing an earlier estimate). `stash_id` points at the
    raw output and what Claude was shown instead, for the per-turn preview."""
    if raw <= kept and not force:
        return
    with connect() as db:
        db.execute("INSERT INTO events (ts, session, feature, detail, raw_tokens, kept_tokens, project, stash_id) "
                   "VALUES (?,?,?,?,?,?,?,?)", (time.time(), session, feature, detail[:200], raw, kept, project, stash_id))


def passed(tool: str, tokens: int, detail: str, reason: str, session: str = "", project: str = "") -> None:
    """Log a tool output Kompactor saw and left as it was, and why, so the dashboard can list it."""
    with connect() as db:
        db.execute("INSERT INTO passes VALUES (?,?,?,?,?,?,?)",
                   (time.time(), session, project, tool, detail[:200], tokens, reason))


def delete(project: str = "", since: float = 0.0, until: float = 0.0) -> int:
    """Delete recorded history: everything, one project's, or what came between `since` and `until`
    (0: no bound), or both. Returns the number of rows removed."""
    until = until or float("inf")
    where, args = "ts >= ? AND ts <= ?", [since, until]
    if project:
        where += " AND project = ?"
        args.append(project)
    n = 0
    with connect() as db:
        sessions = "SELECT session FROM sessions WHERE project = ?" if project else "SELECT session FROM sessions"
        sargs = [project] if project else []
        n += db.execute(f"DELETE FROM calls WHERE ts >= ? AND ts <= ? AND session IN ({sessions})",
                        [since, until] + sargs).rowcount
        for table in ("events", "turns", "passes"):
            n += db.execute(f"DELETE FROM {table} WHERE {where}", args).rowcount
        # a session goes with it once nothing it recorded is left
        gone = f"COALESCE(started, 0) >= ? AND COALESCE(started, 0) <= ?{' AND project = ?' if project else ''} " \
               "AND session NOT IN (SELECT session FROM turns UNION SELECT session FROM events)"
        for table in ("context", "reads", "flags"):
            db.execute(f"DELETE FROM {table} WHERE session IN (SELECT session FROM sessions WHERE {gone})", args)
        n += db.execute(f"DELETE FROM sessions WHERE {gone}", args).rowcount
        n += db.execute(f"DELETE FROM stash WHERE {where}", args).rowcount
        if db.fts:
            db.execute("INSERT INTO stash_fts(stash_fts) VALUES ('rebuild')")
    return n


def passes_page(days: float, project: str = "", page: int = 0, size: int = 10) -> dict:
    """One page of the tool outputs left as they were, newest first, with the totals."""
    where, args = "ts > ?", [time.time() - days * 86400]
    if project:
        where += " AND project = ?"
        args.append(project)
    with connect() as db:
        total, toks = db.execute(f"SELECT COUNT(*), COALESCE(SUM(tokens),0) FROM passes WHERE {where}", args).fetchone()
        rows = db.execute(f"SELECT ts, project, tool, detail, tokens, reason FROM passes WHERE {where} "
                          f"ORDER BY ts DESC LIMIT ? OFFSET ?", args + [size, page * size]).fetchall()
    return {"total": total, "tokens": toks, "page": page, "size": size,
            "items": [{"ts": r[0], "project": r[1], "tool": r[2], "detail": r[3], "tokens": r[4], "reason": r[5]}
                      for r in rows]}


def projects() -> list:
    """Every project Kompactor has seen a session in, most recent first."""
    with connect() as db:
        return [r[0] for r in db.execute(
            "SELECT project, MAX(ts) AS t FROM (SELECT project, COALESCE(NULLIF(last_turn, 0), started) AS ts FROM sessions "
            "UNION ALL SELECT project, ts FROM events UNION ALL SELECT project, ts FROM passes) "
            "WHERE project != '' GROUP BY project ORDER BY t DESC LIMIT 50")]


# ---------------------------------------------------------------------------
# turns


def close_turn(session: str, project: str, context_tokens: int = 0):
    """Summarise savings since the previous turn ended. Returns (turn, session_totals)."""
    now = time.time()
    with connect() as db:
        row = db.execute("SELECT last_turn, compacted, turns FROM sessions WHERE session=?", (session,)).fetchone()
        if row is None:
            db.execute("INSERT INTO sessions (session, project, started, last_turn, compacted, turns) "
                       "VALUES (?,?,?,?,?,?)", (session, project, now, 0, 0, 0))
            row = (0, 0, 0)
        last, compacted, n = row
        feats = db.execute("SELECT feature, SUM(raw_tokens), SUM(kept_tokens) FROM events WHERE session=? AND ts>? "
                           "GROUP BY feature", (session, last or 0)).fetchall()
        raw = sum(f[1] for f in feats)
        kept = sum(f[2] for f in feats)
        by_feature = {f[0]: f[1] - f[2] for f in feats}
        n += 1
        db.execute("UPDATE sessions SET last_turn=?, turns=?, project=? WHERE session=?", (now, n, project, session))
        db.execute("INSERT INTO turns VALUES (?,?,?,?,?,?,?,?)",
                   (session, n, now, project, raw, kept, context_tokens, json.dumps(by_feature)))
        tot = db.execute("SELECT COALESCE(SUM(raw_tokens),0), COALESCE(SUM(kept_tokens),0) FROM events "
                         "WHERE session=?", (session,)).fetchone()
        live = db.execute("SELECT COALESCE(SUM(raw_tokens - kept_tokens),0) FROM events WHERE session=? AND ts>?",
                          (session, compacted or 0)).fetchone()[0]
    turn = {"idx": n, "raw": raw, "kept": kept, "saved": raw - kept, "features": by_feature}
    totals = {"raw": tot[0], "kept": tot[1], "saved": tot[0] - tot[1], "in_context_saved": live,
              "context": context_tokens}
    return turn, totals


def note_context(session: str, tokens: int, model: str = "") -> None:
    """The context size and model Claude Code hands the status line (context_window.total_input_tokens,
    model.id). Kompactor never reads session transcripts for them."""
    with connect() as db:
        if tokens:
            db.execute("INSERT OR REPLACE INTO context VALUES (?,?,?)", (session, int(tokens), time.time()))
        if model:
            db.execute("INSERT OR IGNORE INTO sessions (session, project, started, last_turn, compacted, turns) "
                       "VALUES (?,?,?,?,?,?)", (session, "", time.time(), 0, 0, 0))
            db.execute("UPDATE sessions SET model=? WHERE session=?", (model, session))


def tick(session: str, kind: str = "tool") -> None:
    """One tool call (each one sends Claude a new request that re-reads the context) or a compaction."""
    with connect() as db:
        db.execute("INSERT INTO calls VALUES (?,?,?)", (session, time.time(), kind))


def context_size(session: str) -> int:
    with connect() as db:
        row = db.execute("SELECT tokens FROM context WHERE session=?", (session,)).fetchone()
    return row[0] if row else 0


def session_totals(session: str) -> dict:
    """Savings so far for one session (for status lines when several sessions run at once)."""
    with connect() as db:
        tot = db.execute("SELECT COALESCE(SUM(raw_tokens),0), COALESCE(SUM(kept_tokens),0) FROM events WHERE session=?",
                         (session,)).fetchone()
        row = db.execute("SELECT compacted FROM sessions WHERE session=?", (session,)).fetchone()
        live = db.execute("SELECT COALESCE(SUM(raw_tokens - kept_tokens),0) FROM events WHERE session=? AND ts>?",
                          (session, (row[0] if row else 0) or 0)).fetchone()[0]
        last = db.execute("SELECT raw_tokens, kept_tokens, context_tokens FROM turns WHERE session=? ORDER BY idx DESC "
                          "LIMIT 1", (session,)).fetchone()
    return {"raw": tot[0], "kept": tot[1], "saved": tot[0] - tot[1], "in_context_saved": live,
            "context": last[2] if last else 0, "last_turn_saved": (last[0] - last[1]) if last else 0}


# API list prices in USD per million tokens: (input, cache read). A prompt-cache write costs 1.25x the input
# price (5-minute TTL, what Claude Code uses). Matched by prefix, most specific first.
PRICES = [
    ("claude-fable-5-1", 10.0, 0.25), ("claude-mythos-5-1", 10.0, 0.25),
    ("claude-fable-5", 10.0, 1.0), ("claude-mythos-5", 10.0, 1.0),
    ("claude-opus-5-5", 4.0, 0.20), ("claude-opus-5", 5.0, 0.50),
    ("claude-opus-4-5", 5.0, 0.50), ("claude-opus-4-6", 5.0, 0.50), ("claude-opus-4-7", 5.0, 0.50),
    ("claude-opus-4-8", 5.0, 0.50), ("claude-opus-4", 15.0, 1.50),
    ("claude-sonnet-5", 2.0, 0.20), ("claude-sonnet-4", 3.0, 0.30), ("claude-3-7-sonnet", 3.0, 0.30),
    ("claude-haiku-5-5", 0.10, 0.01), ("claude-haiku-4-5", 1.0, 0.10), ("claude-3-5-haiku", 0.80, 0.08),
]
ALIASES = {"fable": "claude-fable-5-1", "opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5",
           "haiku": "claude-haiku-5-5"}
CACHE_WRITE = 1.25


def model_price(model: str):
    """(name, input, cache read) for a model id or alias as Claude Code reports it, or None if unknown."""
    m = (model or "").lower().split("[")[0].strip()
    m = m[m.find("claude-"):] if "claude-" in m else next((v for k, v in ALIASES.items() if m.startswith(k)), m)
    for prefix, inp, read in PRICES:
        if m.startswith(prefix):
            parts = [p for p in m.split("@")[0].split("-")[1:] if not (p.isdigit() and len(p) > 2)]  # no dates
            name = " ".join(p.title() for p in parts if not p.isdigit()) + " " + ".".join(p for p in parts if p.isdigit())
            return name, inp, read
    return None


def _settings_model() -> str:
    try:
        return json.loads((Path.home() / ".claude" / "settings.json").read_text()).get("model") or ""
    except (OSError, ValueError, AttributeError):
        return ""


def savings(price_per_mtok: float = None, session: str = "", project: str = "") -> dict:
    """Tokens kept out of Claude's context and what they would have cost. Each saving is priced at the API
    rates of the model its session ran on (from the status line): its tokens would have been written to the
    prompt cache once (1.25x input) and re-read by every later request until the session compacted (one per
    tool call and one per new prompt, at the cache-read price). The model comes from the SessionStart hook and
    the status line. `price_per_mtok` overrides the input price (cache reads at 0.1x); sessions whose model is
    unknown use the model in ~/.claude/settings.json, else $3."""
    now = time.time()
    day = now - 86400
    fallback = model_price(_settings_model()) or ("model not reported ($3/M)", 3.0, 0.30)
    with connect() as db:
        def total(where="1", args=()):
            r = db.execute(f"SELECT COUNT(*), COALESCE(SUM(raw_tokens),0), COALESCE(SUM(kept_tokens),0) FROM events "
                           f"WHERE {where}", args).fetchone()
            return {"events": r[0], "raw": r[1], "kept": r[2], "saved": r[1] - r[2], "usd": 0.0}
        periods = {"all": total(), "today": total("ts > ?", (day,))}
        if session:
            periods["session"] = total("session = ?", (session,))
        if project:
            periods["project"] = total("project = ?", (project,))
        recent = db.execute("SELECT session, idx, ts, raw_tokens, kept_tokens, features FROM turns "
                            "WHERE project = ? OR (? = '' AND session = ?) ORDER BY ts DESC LIMIT 30",
                            (project, project, session)).fetchall()
        shortened = {}  # what each recent reply shortened: its commands and files, biggest first
        bounds = {}     # (session, prev turn end, turn end) of each recent reply
        for s, idx, ts, *_ in recent:
            prev = db.execute("SELECT COALESCE(MAX(ts), 0) FROM turns WHERE session = ? AND idx < ?", (s, idx)).fetchone()[0]
            bounds[(s, idx)] = (prev, ts)
            items = {}
            for f, d, r, k in db.execute("SELECT feature, detail, raw_tokens, kept_tokens FROM events WHERE session = ? "
                                         "AND ts > ? AND ts <= ? AND raw_tokens > kept_tokens", (s, prev, ts)):
                it = items.setdefault(_label(f, d), {"what": _label(f, d), "saved": 0, "times": 0})
                it["saved"] += r - k
                it["times"] += 1
            shortened[(s, idx)] = sorted(items.values(), key=lambda it: -it["saved"])[:3]
        events = db.execute("SELECT e.session, e.ts, e.raw_tokens - e.kept_tokens, e.project, COALESCE(s.model, '') "
                            "FROM events e LEFT JOIN sessions s USING (session)").fetchall()
        calls, compactions, prompts = {}, {}, {}
        for s, ts, kind in db.execute("SELECT session, ts, kind FROM calls ORDER BY ts"):
            (compactions if kind == "compact" else calls).setdefault(s, []).append(ts)
        for s, ts in db.execute("SELECT session, ts FROM turns ORDER BY ts"):
            prompts.setdefault(s, []).append(ts)
        top = db.execute("SELECT detail, COUNT(*), SUM(raw_tokens), SUM(kept_tokens) FROM events WHERE feature='bash' "
                         "GROUP BY detail ORDER BY SUM(raw_tokens) - SUM(kept_tokens) DESC LIMIT 5").fetchall()
        sessions = db.execute("SELECT COUNT(DISTINCT session) FROM events").fetchone()[0]
    models, turn_usd = {}, {}
    for s, ts, saved, proj, model in events:
        if price_per_mtok is not None:
            name, inp, read = "your price", price_per_mtok, price_per_mtok * 0.1
        else:
            name, inp, read = model_price(model) or fallback
        until = next((c for c in compactions.get(s, ()) if c > ts), float("inf"))
        rereads = (bisect.bisect_left(calls.get(s, []), until) - bisect.bisect_right(calls.get(s, []), ts)
                   + max(0, bisect.bisect_left(prompts.get(s, []), until) - bisect.bisect_right(prompts.get(s, []), ts) - 1))
        usd = saved * (inp * CACHE_WRITE + read * rereads) / 1e6
        m = models.setdefault(name, {"model": name, "input": inp, "cache_write": inp * CACHE_WRITE, "cache_read": read,
                                     "saved": 0, "rereads": 0, "usd": 0.0, "known": bool(model) or price_per_mtok is not None})
        m["saved"] += saved
        m["rereads"] += rereads * max(saved, 0)
        m["usd"] += usd
        for k, hit in (("all", True), ("today", ts > day), ("session", s == session),
                       ("project", bool(project) and proj == project)):
            if hit and k in periods:
                periods[k]["usd"] += usd
        for key, (lo, hi) in bounds.items():
            if key[0] == s and lo < ts <= hi:
                turn_usd[key] = turn_usd.get(key, 0.0) + usd
    for p in periods.values():
        p["usd"] = round(p["usd"], 6)
    for m in models.values():
        m["usd"] = round(m["usd"], 6)
    return {"price_per_mtok": price_per_mtok, "sessions": sessions, **periods,
            "pricing": sorted(models.values(), key=lambda m: -m["saved"]),
            "top": [{"cmd": t[0], "runs": t[1], "raw": t[2], "kept": t[3]} for t in top],
            "turns": [{"session": t[0], "idx": t[1], "ts": t[2], "raw": t[3], "kept": t[4], "saved": t[3] - t[4],
                       "usd": round(turn_usd.get((t[0], t[1]), 0.0), 6),
                       "features": json.loads(t[5] or "{}"), "shortened": shortened[(t[0], t[1])]} for t in recent]}


def _label(feature: str, detail: str) -> str:
    """How a saving reads in a list: the command, or the file that was outlined or not re-read."""
    name = os.path.basename((detail or "").split(" (")[0])
    return {"read_outline": f"read {name}", "read_dedupe": f"re-read {name}"}.get(feature, detail or feature)


def prune(retention_days: float) -> None:
    """Drop data older than the retention window (called at session start)."""
    cutoff = time.time() - retention_days * 86400
    with connect() as db:
        db.execute("DELETE FROM stash WHERE ts < ?", (min(cutoff, time.time() - 7 * 86400),))
        if db.fts:
            db.execute("INSERT INTO stash_fts(stash_fts) VALUES ('rebuild')")
        for table in ("events", "turns", "calls", "passes"):
            db.execute(f"DELETE FROM {table} WHERE ts < ?", (cutoff,))
        db.execute("DELETE FROM reads WHERE ts < ?", (time.time() - 2 * 86400,))
        db.execute("DELETE FROM flags WHERE ts < ?", (time.time() - 2 * 86400,))
        db.execute("DELETE FROM context WHERE ts < ?", (time.time() - 2 * 86400,))
        db.execute("DELETE FROM sessions WHERE COALESCE(NULLIF(last_turn, 0), started) < ?", (cutoff,))


def once(session: str, key: str) -> bool:
    """True the first time (session, key) is seen; False afterwards (until compaction resets it)."""
    with connect() as db:
        cur = db.execute("INSERT OR IGNORE INTO flags VALUES (?,?,?)", (session, key, time.time()))
        return cur.rowcount == 1


def mark_compacted(session: str) -> None:
    with connect() as db:
        db.execute("UPDATE sessions SET compacted=? WHERE session=?", (time.time(), session))
        db.execute("INSERT INTO calls VALUES (?,?,?)", (session, time.time(), "compact"))
        db.execute("DELETE FROM reads WHERE session=?", (session,))
        db.execute("DELETE FROM flags WHERE session=?", (session,))


def write_live(payload: dict) -> None:
    """Small JSON file the VS Code extension and the status line read."""
    p = home() / "live.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    os.replace(tmp, p)


def read_live() -> dict:
    try:
        return json.loads((home() / "live.json").read_text())
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# stash


STASH_MAX_CHARS = 2_000_000


def stash(cmd: str, output: str, session: str = "", project: str = "", code: int = 0) -> int:
    if len(output) > STASH_MAX_CHARS:
        output = output[:STASH_MAX_CHARS] + f"\n[kompactor: stash truncated at {STASH_MAX_CHARS} chars]"
    with connect() as db:
        cur = db.execute("INSERT INTO stash (ts, cmd, output, session, project, code) VALUES (?,?,?,?,?,?)",
                         (time.time(), cmd, output, session, project, code))
        rowid = cur.lastrowid
        if db.fts:
            db.execute("INSERT INTO stash_fts (rowid, output) VALUES (?,?)", (rowid, output))
        # keep the stash bounded
        db.execute("DELETE FROM stash WHERE id <= ?", (rowid - 500,))
        return rowid


def set_shown(sid: int, text: str) -> None:
    """What Claude was shown in place of stashed output `sid`."""
    with connect() as db:
        db.execute("UPDATE stash SET shown=? WHERE id=?", (text, sid))


PREVIEW_CHARS = 60_000  # per output, so a huge log can't stall the dashboard


def turn_outputs(session: str, idx: int) -> list:
    """What one reply shortened: each saving with, for command output, its raw text and what Claude saw."""
    with connect() as db:
        row = db.execute("SELECT ts FROM turns WHERE session=? AND idx=?", (session, idx)).fetchone()
        if row is None:
            return []
        prev = db.execute("SELECT COALESCE(MAX(ts), 0) FROM turns WHERE session=? AND idx<?", (session, idx)).fetchone()[0]
        rows = db.execute("SELECT e.feature, e.detail, e.raw_tokens, e.kept_tokens, s.output, s.shown FROM events e "
                          "LEFT JOIN stash s ON s.id = e.stash_id AND e.stash_id > 0 WHERE e.session=? AND e.ts>? "
                          "AND e.ts<=? AND e.raw_tokens > e.kept_tokens ORDER BY e.raw_tokens - e.kept_tokens DESC",
                          (session, prev, row[0])).fetchall()
    return [{"feature": f, "what": _label(f, d), "raw": r, "kept": k,
             "before": (out or "")[:PREVIEW_CHARS], "after": (shown or "")[:PREVIEW_CHARS]}
            for f, d, r, k, out, shown in rows]


def project_outputs(project: str = "", limit: int = 12) -> list:
    """The latest stashed command outputs, one per command, from one project or (empty) every project: the real
    data behind the live preview and each level's savings figure."""
    where, args = ("WHERE project=?", [project]) if project else ("", [])
    with connect() as db:
        return [{"id": f"s{i}", "cmd": c, "text": o[:PREVIEW_CHARS], "code": code, "project": pr}
                for i, c, o, code, pr in db.execute(
                    f"SELECT id, cmd, output, code, project FROM stash WHERE id IN (SELECT MAX(id) FROM stash {where} "
                    f"GROUP BY cmd) ORDER BY id DESC LIMIT ?", args + [limit])]


def get_stash(sid: int):
    with connect() as db:
        return db.execute("SELECT cmd, output FROM stash WHERE id=?", (sid,)).fetchone()


def search_stash(query: str, limit: int = 20):
    """Return (id, cmd, matching lines) for stashed outputs containing query."""
    with connect() as db:
        if db.fts:
            try:
                ids = [r[0] for r in db.execute(
                    "SELECT rowid FROM stash_fts WHERE stash_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit))]
            except sqlite3.OperationalError:  # query isn't valid FTS syntax
                ids = None
        else:
            ids = None
        if ids is None:
            ids = [r[0] for r in db.execute(
                "SELECT id FROM stash WHERE output LIKE ? ORDER BY id DESC LIMIT ?", (f"%{query}%", limit))]
        rows = []
        terms = [t.lower() for t in query.replace('"', "").split() if t.upper() not in ("AND", "OR", "NOT")]
        for sid in ids:
            cmd, out = db.execute("SELECT cmd, output FROM stash WHERE id=?", (sid,)).fetchone()
            hits = [(i + 1, ln) for i, ln in enumerate(out.splitlines()) if any(t in ln.lower() for t in terms)]
            rows.append((sid, cmd, hits))
        return rows
