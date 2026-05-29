import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "lab.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    form_type TEXT,
    name TEXT,
    email TEXT,
    phone TEXT,
    company TEXT,
    message TEXT,
    source_page TEXT,
    consent_type TEXT,
    privacy_link_present INTEGER DEFAULT 0,
    profile_mode TEXT
);

CREATE TABLE IF NOT EXISTS routing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER,
    route_type TEXT,
    destination TEXT,
    status TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS processor_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER,
    processor_name TEXT,
    processor_type TEXT,
    evidence TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS consent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER,
    consent_type TEXT,
    text_snapshot TEXT,
    checkbox_present INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    page TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

async def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executescript(SCHEMA)
        await db.commit()
