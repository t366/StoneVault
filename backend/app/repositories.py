import json
import sqlite3
from typing import Any

from .database import Database


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        *,
        name: str,
        source_path: str,
        hdd_rel_path: str,
        schedule_cron: str | None = None,
        filter_extensions: list[str] | None = None,
        filter_min_size: int | None = None,
        filter_max_size: int | None = None,
        backup_mode: str = "full",
        enabled: int = 1,
    ) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO tasks (name, source_path, hdd_rel_path, schedule_cron,
                                   filter_extensions, filter_min_size, filter_max_size,
                                   backup_mode, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    source_path,
                    hdd_rel_path,
                    schedule_cron,
                    json.dumps(filter_extensions or []),
                    filter_min_size,
                    filter_max_size,
                    backup_mode,
                    enabled,
                ),
            )
            return cur.lastrowid

    def get(self, task_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self._row_to_dict(row)

    def list(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
            return [self._row_to_dict(r) for r in rows]

    def update(self, task_id: int, **fields: Any) -> None:
        allowed = {
            "name",
            "source_path",
            "hdd_rel_path",
            "schedule_cron",
            "filter_extensions",
            "filter_min_size",
            "filter_max_size",
            "backup_mode",
            "enabled",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "filter_extensions" in updates:
            updates["filter_extensions"] = json.dumps(updates["filter_extensions"] or [])
        updates["updated_at"] = "datetime('now')"
        columns = ", ".join(f"{k} = ?" for k in updates)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE tasks SET {columns}, updated_at = datetime('now') WHERE id = ?",
                (*updates.values(), task_id),
            )

    def delete(self, task_id: int) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result = dict(row)
        try:
            result["filter_extensions"] = json.loads(result.get("filter_extensions") or "[]")
        except json.JSONDecodeError:
            result["filter_extensions"] = []
        return result


class SnapshotRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, *, task_id: int, started_at: str, status: str = "running") -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO snapshots (task_id, started_at, status) VALUES (?, ?, ?)",
                (task_id, started_at, status),
            )
            return cur.lastrowid

    def get(self, snapshot_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
            return dict(row) if row else None

    def list_by_task(self, task_id: int) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM snapshots WHERE task_id = ? ORDER BY id DESC", (task_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def finish(
        self,
        snapshot_id: int,
        *,
        status: str,
        file_count: int = 0,
        total_bytes: int = 0,
        error_message: str | None = None,
    ) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE snapshots
                SET finished_at = datetime('now'), status = ?, file_count = ?,
                    total_bytes = ?, error_message = ?
                WHERE id = ?
                """,
                (status, file_count, total_bytes, error_message, snapshot_id),
            )


class FileIndexRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        *,
        snapshot_id: int,
        rel_path: str,
        file_size: int,
        md5: str | None = None,
        mtime: str | None = None,
        ssd_cache_path: str | None = None,
        hdd_source_path: str | None = None,
        content_type: str | None = None,
        filename: str | None = None,
        body: str = "",
        ai_text: str = "",
    ) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO file_index (snapshot_id, rel_path, file_size, md5, mtime,
                                        ssd_cache_path, hdd_source_path, content_type,
                                        filename, body, ai_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    rel_path,
                    file_size,
                    md5,
                    mtime,
                    ssd_cache_path,
                    hdd_source_path,
                    content_type,
                    filename or rel_path,
                    body,
                    ai_text,
                ),
            )
            file_id = cur.lastrowid
            conn.execute(
                "INSERT INTO file_fts (rowid, filename, body, ai_text) VALUES (?, ?, ?, ?)",
                (file_id, filename or rel_path, body, ai_text),
            )
            return file_id

    def get(self, file_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM file_index WHERE id = ?", (file_id,)).fetchone()
            return dict(row) if row else None

    def list_by_snapshot(self, snapshot_id: int) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM file_index WHERE snapshot_id = ? ORDER BY id", (snapshot_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def find_by_rel_path(self, rel_path: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM file_index WHERE rel_path = ? ORDER BY id DESC LIMIT 1",
                (rel_path,),
            ).fetchone()
            return dict(row) if row else None

    def update_text(self, file_id: int, *, body: str, ai_text: str) -> None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT filename, body, ai_text FROM file_index WHERE id = ?", (file_id,)
            ).fetchone()
            if row is not None:
                conn.execute(
                    "INSERT INTO file_fts (file_fts, rowid, filename, body, ai_text)"
                    " VALUES ('delete', ?, ?, ?, ?)",
                    (file_id, row["filename"], row["body"], row["ai_text"]),
                )
            conn.execute(
                "UPDATE file_index SET body = ?, ai_text = ? WHERE id = ?",
                (body, ai_text, file_id),
            )
            filename = row["filename"] if row is not None else ""
            conn.execute(
                "INSERT INTO file_fts (rowid, filename, body, ai_text) VALUES (?, ?, ?, ?)",
                (file_id, filename, body, ai_text),
            )

    def delete(self, file_id: int) -> None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT filename, body, ai_text FROM file_index WHERE id = ?",
                (file_id,),
            ).fetchone()
            if row is not None:
                conn.execute(
                    "INSERT INTO file_fts (file_fts, rowid, filename, body, ai_text)"
                    " VALUES ('delete', ?, ?, ?, ?)",
                    (file_id, row["filename"], row["body"], row["ai_text"]),
                )
            conn.execute("DELETE FROM file_index WHERE id = ?", (file_id,))


class MetadataRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, *, file_id: int, kind: str, value: Any) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO metadata (file_id, kind, value_json) VALUES (?, ?, ?)",
                (file_id, kind, json.dumps(value)),
            )
            return cur.lastrowid

    def list_by_file(self, file_id: int) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM metadata WHERE file_id = ? ORDER BY id", (file_id,)
            ).fetchall()
            return [dict(r) for r in rows]


class AdminUserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, *, username: str, password_hash: str) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            return cur.lastrowid

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM admin_user WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None


class AiJobRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def enqueue(self, *, file_id: int, job_type: str, priority: int = 10) -> int:
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO ai_jobs (file_id, job_type, priority) VALUES (?, ?, ?)",
                (file_id, job_type, priority),
            )
            return cur.lastrowid

    def get(self, job_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM ai_jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def update_status(self, job_id: int, status: str) -> None:
        with self.db.connect() as conn:
            conn.execute("UPDATE ai_jobs SET status = ? WHERE id = ?", (status, job_id))

    def pending(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ai_jobs WHERE status = 'pending' ORDER BY priority, id"
            ).fetchall()
            return [dict(r) for r in rows]

    def running_count(self) -> int:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM ai_jobs WHERE status = 'running'"
            ).fetchone()
            return int(row["n"])
