import aiosqlite
from contextlib import asynccontextmanager


CREATE_SCANS_TABLE = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    data_categories TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT,
    network_observations TEXT,
    screenshot_path TEXT,
    registration_relevance TEXT,
    raw_json_export_path TEXT,
    markdown_export_path TEXT,
    visited_pages TEXT,
    site_summary TEXT,
    vendor_summary TEXT,
    policy_analysis TEXT,
    synthetic_submission_enabled INTEGER DEFAULT 0,
    synthetic_submission_summary TEXT,
    operator_integration_evidence TEXT,
    processor_map TEXT,
    fz152_assessment TEXT,
    operator_metadata TEXT
)
"""

# Columns added after initial schema creation — applied via ALTER TABLE if missing
_MIGRATION_COLUMNS: list[tuple[str, str]] = [
    ("network_observations", "TEXT"),
    ("screenshot_path", "TEXT"),
    ("registration_relevance", "TEXT"),
    ("raw_json_export_path", "TEXT"),
    ("markdown_export_path", "TEXT"),
    ("visited_pages", "TEXT"),
    ("site_summary", "TEXT"),
    ("vendor_summary", "TEXT"),
    ("policy_analysis", "TEXT"),
    ("synthetic_submission_enabled", "INTEGER DEFAULT 0"),
    ("synthetic_submission_summary", "TEXT"),
    ("operator_integration_evidence", "TEXT"),
    ("processor_map", "TEXT"),
    ("fz152_assessment", "TEXT"),
    ("operator_metadata", "TEXT"),
]


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_SCANS_TABLE)
        await db.commit()
        # Add new columns to pre-existing databases (no-op if column already exists)
        async with db.execute("PRAGMA table_info(scans)") as cursor:
            existing_cols = {row[1] async for row in cursor}
        for col_name, col_type in _MIGRATION_COLUMNS:
            if col_name not in existing_cols:
                await db.execute(
                    f"ALTER TABLE scans ADD COLUMN {col_name} {col_type}"
                )
        await db.commit()


@asynccontextmanager
async def get_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db
