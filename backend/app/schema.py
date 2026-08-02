SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    hdd_rel_path TEXT NOT NULL,
    schedule_cron TEXT,
    filter_extensions TEXT NOT NULL DEFAULT '[]',
    filter_min_size INTEGER,
    filter_max_size INTEGER,
    backup_mode TEXT NOT NULL DEFAULT 'full'
        CHECK (backup_mode IN ('full', 'incremental')),
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'success', 'failed', 'skipped')),
    file_count INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_snapshots_task ON snapshots(task_id);

CREATE TABLE IF NOT EXISTS file_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    md5 TEXT,
    mtime TEXT,
    ssd_cache_path TEXT,
    hdd_source_path TEXT,
    content_type TEXT,
    filename TEXT,
    body TEXT NOT NULL DEFAULT '',
    ai_text TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_file_index_rel_path ON file_index(rel_path);
CREATE INDEX IF NOT EXISTS idx_file_index_snapshot ON file_index(snapshot_id);

CREATE VIRTUAL TABLE IF NOT EXISTS file_fts USING fts5(
    filename,
    body,
    ai_text,
    content='file_index',
    content_rowid='id',
    tokenize='trigram'
);

CREATE TABLE IF NOT EXISTS metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES file_index(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    value_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metadata_file ON metadata(file_id);

CREATE TABLE IF NOT EXISTS admin_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES file_index(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'done', 'failed')),
    priority INTEGER NOT NULL DEFAULT 10,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_status ON ai_jobs(status);
"""
