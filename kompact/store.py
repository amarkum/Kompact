"""Local SQLite store: savings ledger, stashed raw outputs (FTS5), read tracker."""

import os
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    ts REAL, session TEXT, feature TEXT, detail TEXT,
    raw_tokens INTEGER, kept_tokens INTEGER
);
CREATE TABLE IF NOT EXISTS stash (
    id INTEGER PRIMARY KEY, ts REAL, cmd TEXT, output TEXT
);
CREATE TABLE IF NOT EXISTS reads (
    session TEXT, path TEXT, sig TEXT, state TEXT, pending INTEGER DEFAULT 0, ts REAL,
    PRIMARY KEY (session, path)
);
"""


def home() -> Path:
    p = Path(os.environ.get("KOMPACT_HOME", Path.home() / ".kompact"))
    p.mkdir(parents=True, exist_ok=True)
    return p


class _Conn(sqlite3.Connection):
    fts = False


def connect() -> _Conn:
    db = sqlite3.connect(home() / "kompact.db", timeout=5, factory=_Conn)
    db.executescript(SCHEMA)
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS stash_fts USING fts5(output, content='stash', content_rowid='id')")
        db.fts = True
    except sqlite3.OperationalError:  # sqlite built without FTS5
        db.fts = False
    return db


def record(feature: str, raw: int, kept: int, detail: str = "", session: str = "", force: bool = False) -> None:
    """Log a saving. `force` allows negative entries (reversing an earlier estimate)."""
    if raw <= kept and not force:
        return
    with connect() as db:
        db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)", (time.time(), session, feature, detail[:200], raw, kept))


def stash(cmd: str, output: str) -> int:
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
