"""Recipe data-access layer (SQLite, local file). All queries are parameterised."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,              -- 'epicurious-13k' | 'user' | 'generated'
    source_ref      TEXT,                       -- row id / slug in the original source
    title           TEXT NOT NULL,
    ingredients     TEXT NOT NULL,              -- JSON list of raw ingredient lines (original text kept)
    instructions    TEXT NOT NULL DEFAULT '',
    image_name      TEXT,
    cuisine         TEXT,                       -- user/source-declared only
    meal_type       TEXT,                       -- user/source-declared only
    total_time_min  INTEGER,                    -- user/source-declared only
    servings        REAL,
    nutrition       TEXT,                       -- JSON, user/source-declared only (per serving)
    nutrition_source TEXT,                      -- e.g. 'user-entered'; NULL = unknown
    diet_tags       TEXT,                       -- JSON list declared by the author
    owner_id        TEXT,
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL,
    deleted         INTEGER NOT NULL DEFAULT 0,
    version         INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_recipes_source ON recipes(source);
CREATE INDEX IF NOT EXISTS idx_recipes_owner ON recipes(owner_id);

-- Prior versions of edited/deleted recipes (reversible edits).
CREATE TABLE IF NOT EXISTS recipe_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id   INTEGER NOT NULL,
    version     INTEGER NOT NULL,
    snapshot    TEXT NOT NULL,
    changed_at  REAL NOT NULL,
    changed_by  TEXT
);

CREATE TABLE IF NOT EXISTS user_prefs (
    user_id     TEXT PRIMARY KEY,
    prefs       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    recipe_id   INTEGER NOT NULL,
    kind        TEXT NOT NULL,      -- 'view' | 'rating' | 'favorite'
    value       REAL,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id, kind);

CREATE TABLE IF NOT EXISTS search_feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT,
    query       TEXT NOT NULL,
    recipe_id   INTEGER NOT NULL,
    helpful     INTEGER NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_searches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    query       TEXT NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

RECIPE_COLUMNS = (
    "id, source, source_ref, title, ingredients, instructions, image_name, cuisine, meal_type, "
    "total_time_min, servings, nutrition, nutrition_source, diet_tags, owner_id, created_at, updated_at, version"
)

_lock = threading.Lock()
_listeners: list = []


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = connect()
        _conn.executescript(SCHEMA)
    return _conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    with _lock:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def on_change(callback) -> None:
    """Register a callback(recipe_id, action) fired after recipe writes (used for incremental indexing)."""
    _listeners.append(callback)


def _notify(recipe_id: int, action: str) -> None:
    for cb in _listeners:
        cb(recipe_id, action)


def row_to_recipe(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["ingredients"] = json.loads(d["ingredients"] or "[]")
    d["nutrition"] = json.loads(d["nutrition"]) if d.get("nutrition") else None
    d["diet_tags"] = json.loads(d["diet_tags"]) if d.get("diet_tags") else []
    return d


def get_recipe(recipe_id: int) -> dict[str, Any] | None:
    row = get_conn().execute(
        f"SELECT {RECIPE_COLUMNS} FROM recipes WHERE id = ? AND deleted = 0", (recipe_id,)
    ).fetchone()
    return row_to_recipe(row) if row else None


def get_recipes(ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    out: dict[int, dict[str, Any]] = {}
    conn = get_conn()
    for i in range(0, len(ids), 500):
        chunk = ids[i : i + 500]
        q = f"SELECT {RECIPE_COLUMNS} FROM recipes WHERE deleted = 0 AND id IN ({','.join('?' * len(chunk))})"
        for row in conn.execute(q, chunk):
            out[row["id"]] = row_to_recipe(row)
    return out


def iter_all_recipes() -> Iterator[dict[str, Any]]:
    for row in get_conn().execute(f"SELECT {RECIPE_COLUMNS} FROM recipes WHERE deleted = 0 ORDER BY id"):
        yield row_to_recipe(row)


def list_recipes(
    offset: int = 0, limit: int = 24, q: str | None = None, source: str | None = None, owner_id: str | None = None
) -> tuple[list[dict[str, Any]], int]:
    where, params = ["deleted = 0"], []
    if q:
        where.append("title LIKE ?")
        params.append(f"%{q}%")
    if source:
        where.append("source = ?")
        params.append(source)
    if owner_id:
        where.append("owner_id = ?")
        params.append(owner_id)
    clause = " AND ".join(where)
    conn = get_conn()
    total = conn.execute(f"SELECT COUNT(*) FROM recipes WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {RECIPE_COLUMNS} FROM recipes WHERE {clause} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return [row_to_recipe(r) for r in rows], total


_WRITABLE = (
    "title", "ingredients", "instructions", "cuisine", "meal_type", "total_time_min",
    "servings", "nutrition", "nutrition_source", "diet_tags",
)


def _encode(field: str, value: Any) -> Any:
    if field in ("ingredients", "diet_tags", "nutrition") and value is not None:
        return json.dumps(value, ensure_ascii=False)
    return value


def create_recipe(data: dict[str, Any], source: str = "user", owner_id: str | None = None) -> int:
    now = time.time()
    fields = [f for f in _WRITABLE if f in data]
    with tx() as conn:
        cur = conn.execute(
            f"INSERT INTO recipes (source, owner_id, created_at, updated_at, {', '.join(fields)}) "
            f"VALUES (?, ?, ?, ?, {', '.join('?' * len(fields))})",
            [source, owner_id, now, now, *[_encode(f, data[f]) for f in fields]],
        )
        rid = int(cur.lastrowid)
    _notify(rid, "create")
    return rid


def _snapshot(conn: sqlite3.Connection, recipe_id: int, changed_by: str | None) -> dict[str, Any] | None:
    row = conn.execute(f"SELECT {RECIPE_COLUMNS} FROM recipes WHERE id = ? AND deleted = 0", (recipe_id,)).fetchone()
    if not row:
        return None
    current = dict(row)
    conn.execute(
        "INSERT INTO recipe_history (recipe_id, version, snapshot, changed_at, changed_by) VALUES (?, ?, ?, ?, ?)",
        (recipe_id, current["version"], json.dumps(current, ensure_ascii=False), time.time(), changed_by),
    )
    return current


def update_recipe(recipe_id: int, data: dict[str, Any], changed_by: str | None = None) -> bool:
    fields = [f for f in _WRITABLE if f in data]
    if not fields:
        return get_recipe(recipe_id) is not None
    with tx() as conn:
        if _snapshot(conn, recipe_id, changed_by) is None:
            return False
        sets = ", ".join(f"{f} = ?" for f in fields)
        conn.execute(
            f"UPDATE recipes SET {sets}, updated_at = ?, version = version + 1 WHERE id = ?",
            [*[_encode(f, data[f]) for f in fields], time.time(), recipe_id],
        )
    _notify(recipe_id, "update")
    return True


def delete_recipe(recipe_id: int, changed_by: str | None = None) -> bool:
    """Soft delete: the row and its history are kept so deletes are reversible."""
    with tx() as conn:
        if _snapshot(conn, recipe_id, changed_by) is None:
            return False
        conn.execute("UPDATE recipes SET deleted = 1, updated_at = ? WHERE id = ?", (time.time(), recipe_id))
    _notify(recipe_id, "delete")
    return True


def recipe_count() -> int:
    return get_conn().execute("SELECT COUNT(*) FROM recipes WHERE deleted = 0").fetchone()[0]


def get_meta(key: str) -> str | None:
    row = get_conn().execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(key: str, value: str) -> None:
    with tx() as conn:
        conn.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
