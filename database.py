"""SQLite storage layer (stdlib only)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import config


SCHEMA = """
CREATE TABLE IF NOT EXISTS licenses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key   TEXT UNIQUE NOT NULL,
    note          TEXT DEFAULT '',
    plan          TEXT DEFAULT '',
    status        TEXT DEFAULT 'active',
    max_devices   INTEGER DEFAULT 1,
    duration_days INTEGER DEFAULT 30,
    activated_at  TEXT,
    expires_at    TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id  INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    device_id   TEXT NOT NULL,
    bundle_id   TEXT DEFAULT '',
    app_version TEXT DEFAULT '',
    activated_at TEXT NOT NULL,
    UNIQUE(license_id, device_id)
);

CREATE TABLE IF NOT EXISTS tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token       TEXT UNIQUE NOT NULL,
    license_id  INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    device_id   TEXT NOT NULL,
    expires_at  INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    revoked     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS patches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT UNIQUE NOT NULL,
    stored_name TEXT NOT NULL,
    game_id     TEXT DEFAULT 'free-fire',
    item_id     TEXT NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT DEFAULT 'mod',
    subtitle    TEXT DEFAULT '',
    package_password TEXT DEFAULT '',
    enabled     INTEGER DEFAULT 1,
    size        INTEGER DEFAULT 0,
    uploaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)


def setting_get(key, default=None):
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def setting_set(key, value):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
