import html
import sqlite3
from typing import Any

from ..database import Database

_SORTABLE = {"id", "filename", "file_size", "mtime", "started_at"}
_DEFAULT_SORT = "id"
_DEFAULT_ORDER = "desc"
_MAX_PAGE_SIZE = 200
_FTS_MIN_QUERY_LEN = 3

_HL_FILENAME_SQL = "highlight(file_fts, 0, '<mark>', '</mark>') AS hl_filename"
_HL_BODY_SQL = "highlight(file_fts, 1, '<mark>', '</mark>') AS hl_body"
_HL_AI_SQL = "highlight(file_fts, 2, '<mark>', '</mark>') AS hl_ai"


def _fts_phrase(q: str) -> str:
    return '"' + q.replace('"', '""') + '"'


def _safe_highlight(value: Any) -> str:
    """转义高亮片段中的 HTML，仅保留 <mark> 标签，防止 XSS。"""
    escaped = html.escape(value or "", quote=False)
    return escaped.replace("&lt;mark&gt;", "<mark>").replace(
        "&lt;/mark&gt;", "</mark>"
    )


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

    def fts_query(
        self,
        *,
        q: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """FTS5 全文检索，返回关键词高亮片段。

        trigram 分词器要求查询词不少于 3 个字符（需求 5.3），
        过短时降级为 filename/body 的 LIKE 模糊匹配。
        """
        query = (q or "").strip()
        page = max(1, int(page))
        page_size = min(max(1, int(page_size)), _MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        empty = {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "mode": "fts" if len(query) >= _FTS_MIN_QUERY_LEN else "like",
        }
        if not query:
            return empty

        with self.db.connect() as conn:
            if len(query) >= _FTS_MIN_QUERY_LEN:
                total = conn.execute(
                    "SELECT COUNT(*) AS n FROM file_fts WHERE file_fts MATCH ?",
                    (_fts_phrase(query),),
                ).fetchone()["n"]
                rows = conn.execute(
                    f"""
                    SELECT fi.*, {_HL_FILENAME_SQL}, {_HL_BODY_SQL}, {_HL_AI_SQL}
                    FROM file_fts
                    JOIN file_index fi ON fi.id = file_fts.rowid
                    WHERE file_fts MATCH ?
                    ORDER BY file_fts.rank
                    LIMIT ? OFFSET ?
                    """,
                    (_fts_phrase(query), page_size, offset),
                ).fetchall()
                mode = "fts"
            else:
                like = f"%{query}%"
                total = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM file_index
                    WHERE filename LIKE ? OR body LIKE ? OR ai_text LIKE ?
                    """,
                    (like, like, like),
                ).fetchone()["n"]
                rows = conn.execute(
                    """
                    SELECT fi.*, '' AS hl_filename, '' AS hl_body, '' AS hl_ai
                    FROM file_index fi
                    WHERE fi.filename LIKE ? OR fi.body LIKE ? OR fi.ai_text LIKE ?
                    ORDER BY fi.id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (like, like, like, page_size, offset),
                ).fetchall()
                mode = "like"

        items = []
        for row in rows:
            item = dict(row)
            item["hl_filename"] = _safe_highlight(item.get("hl_filename"))
            item["hl_body"] = _safe_highlight(item.get("hl_body"))
            item["hl_ai"] = _safe_highlight(item.get("hl_ai"))
            items.append(item)

        return {
            "items": items,
            "total": int(total),
            "page": page,
            "page_size": page_size,
            "mode": mode,
        }
