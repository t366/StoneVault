import sqlite3
from typing import Any

from ..database import Database

_SORTABLE = {"id", "filename", "file_size", "mtime", "started_at"}
_DEFAULT_SORT = "id"
_DEFAULT_ORDER = "desc"
_MAX_PAGE_SIZE = 200


class FileQueryService:
    """文件组合查询：文件名模糊、后缀、时间范围、大小范围、分页排序。

    时间范围基于最近快照的备份时间（snapshots.started_at），
    以 ISO 日期前缀字典序比较，兼容 'YYYY-MM-DD' 与完整 ISO 时间。
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def query(
        self,
        *,
        q: str | None = None,
        ext: str | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = _DEFAULT_SORT,
        order: str = _DEFAULT_ORDER,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []

        if q:
            where.append("fi.filename LIKE ?")
            params.append(f"%{q}%")

        if ext:
            ext_norm = ext.strip().lower()
            if not ext_norm.startswith("."):
                ext_norm = "." + ext_norm
            where.append("LOWER(fi.rel_path) LIKE ?")
            params.append(f"%{ext_norm}")

        if from_time:
            where.append("s.started_at >= ?")
            params.append(str(from_time))
        if to_time:
            where.append("s.started_at <= ?")
            params.append(str(to_time))

        if size_min is not None:
            where.append("fi.file_size >= ?")
            params.append(size_min)
        if size_max is not None:
            where.append("fi.file_size <= ?")
            params.append(size_max)

        where_sql = " AND ".join(where) if where else "1=1"

        if sort_by not in _SORTABLE:
            sort_by = _DEFAULT_SORT
        order_col = f"fi.{sort_by}" if sort_by != "started_at" else "s.started_at"
        direction = "ASC" if order.lower() == "asc" else "DESC"

        page = max(1, int(page))
        page_size = min(max(1, int(page_size)), _MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        with self.db.connect() as conn:
            total = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM file_index fi
                JOIN snapshots s ON fi.snapshot_id = s.id
                WHERE {where_sql}
                """,
                params,
            ).fetchone()["n"]

            rows = conn.execute(
                f"""
                SELECT fi.*, s.started_at AS backup_time, s.task_id
                FROM file_index fi
                JOIN snapshots s ON fi.snapshot_id = s.id
                WHERE {where_sql}
                ORDER BY {order_col} {direction}
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()

        return {
            "items": [dict(r) for r in rows],
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }
