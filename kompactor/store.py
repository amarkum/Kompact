"""Local SQLite store: savings ledger, per-turn summaries, stashed raw outputs
(FTS5), and the Read tracker. Lives in ~/.kompactor (override with KOMPACTOR_HOME)."""

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
    id INTEGER PRIMARY KEY, ts REAL, cmd TEXT, output TEXT
);
CREATE TABLE IF NOT EXISTS reads (
    session TEXT, path TEXT, sig TEXT, state TEXT, pending INTEGER DEFAULT 0, ts REAL,
    PRIMARY KEY (session, path)
);
CREATE TABLE IF NOT EXISTS sessions (
    session TEXT PRIMARY KEY, project TEXT, started REAL, last_turn REAL, compacted REAL DEFAULT 0,
    turns INTEGER DEFAULT 0
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
    db.execute("CREATE INDEX IF NOT EXISTS events_session ON events(session, ts)")
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS stash_fts USING fts5(output, content='stash', content_rowid='id')")
        db.fts = True
    except sqlite3.OperationalError:  # sqlite built without FTS5
        db.fts = False
    return db


def record(feature: str, raw: int, kept: int, detail: str = "", session: str = "", force: bool = False,
           project: str = "") -> None:
    """Log a saving. `force` allows negative entries (reversing an earlier estimate)."""
    if raw <= kept and not force:
        return
    with connect() as db:
        db.execute("INSERT INTO events (ts, session, feature, detail, raw_tokens, kept_tokens, project) "
                   "VALUES (?,?,?,?,?,?,?)", (time.time(), session, feature, detail[:200], raw, kept, project))


# ---------------------------------------------------------------------------
# turns


def close_turn(session: str, project: str, context_tokens: int = 0):
    """Summarise savings since the previous turn ended. Returns (turn, session_totals)."""
    now = time.time()
    with connect() as db:
        row = db.execute("SELECT last_turn, compacted, turns FROM sessions WHERE session=?", (session,)).fetchone()
        if row is None:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)", (session, project, now, 0, 0, 0))
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


def note_context(session: str, tokens: int) -> None:
    """The context size Claude Code hands the status line (context_window.total_input_tokens).
    Kompactor never reads session transcripts for it."""
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO context VALUES (?,?,?)", (session, int(tokens), time.time()))


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


def prune(retention_days: float) -> None:
    """Drop data older than the retention window (called at session start)."""
    cutoff = time.time() - retention_days * 86400
    with connect() as db:
        db.execute("DELETE FROM stash WHERE ts < ?", (min(cutoff, time.time() - 7 * 86400),))
        if db.fts:
            db.execute("INSERT INTO stash_fts(stash_fts) VALUES ('rebuild')")
        for table in ("events", "turns"):
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


def stash(cmd: str, output: str) -> int:
    if len(output) > STASH_MAX_CHARS:
        output = output[:STASH_MAX_CHARS] + f"\n[kompactor: stash truncated at {STASH_MAX_CHARS} chars]"
    with connect() as db:
        cur = db.execute("INSERT INTO stash (ts, cmd, output) VALUES (?,?,?)", (time.time(), cmd, output))
        rowid = cur.lastrowid
        if db.fts:
            db.execute("INSERT INTO stash_fts (rowid, output) VALUES (?,?)", (rowid, output))
        # keep the stash bounded
        db.execute("DELETE FROM stash WHERE id <= ?", (rowid - 500,))
        return rowid


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
