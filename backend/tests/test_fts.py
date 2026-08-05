from app.database import Database
from app.repositories import FileIndexRepository, SnapshotRepository, TaskRepository
from app.query_service import FileQueryService


def _make_db(tmp_path) -> Database:
    db = Database(tmp_path / "db.sqlite")
    db.initialize()
    return db


def _seed(db: Database) -> int:
    repo = TaskRepository(db)
    snapshots = SnapshotRepository(db)
    files = FileIndexRepository(db)
    task_id = repo.create(name="t", source_path="/src", hdd_rel_path="t")
    snap_id = snapshots.create(
        task_id=task_id, started_at="2026-08-01T10:00:00", status="success"
    )
    files.create(
        snapshot_id=snap_id,
        rel_path="docs/年度报告.pdf",
        file_size=100,
        filename="年度报告.pdf",
        body="这是一份关于年度财务情况的完整报告，包含营收与利润数据。",
    )
    files.create(
        snapshot_id=snap_id,
        rel_path="docs/会议纪要.txt",
        file_size=200,
        filename="会议纪要.txt",
        body="本次会议讨论了产品迭代计划与发布时间表。",
    )
    files.create(
        snapshot_id=snap_id,
        rel_path="docs/照片.jpg",
        file_size=300,
        filename="照片.jpg",
        body="",
    )
    return snap_id


def test_fts_match_hits_body_and_filename(tmp_path):
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    result = svc.fts_query(q="年度财务情况")
    assert result["mode"] == "fts"
    assert result["total"] == 1
    assert result["items"][0]["filename"] == "年度报告.pdf"

    result = svc.fts_query(q="产品迭代")
    assert result["total"] == 1
    assert result["items"][0]["filename"] == "会议纪要.txt"


def test_fts_highlight_markup(tmp_path):
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    result = svc.fts_query(q="年度财务情况")
    item = result["items"][0]
    assert "<mark>" in item["hl_body"]
    assert "年度财务情况" in item["hl_body"]


def test_fts_short_query_falls_back_to_like(tmp_path):
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    result = svc.fts_query(q="报告")
    assert result["mode"] == "like"
    assert result["total"] >= 1


def test_fts_pagination(tmp_path):
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    page1 = svc.fts_query(q="报告", page=1, page_size=1)
    page2 = svc.fts_query(q="报告", page=2, page_size=1)
    assert page1["total"] == page2["total"]
    assert len(page1["items"]) == 1
    ids1 = {it["id"] for it in page1["items"]}
    ids2 = {it["id"] for it in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_fts_empty_query(tmp_path):
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    result = svc.fts_query(q="   ")
    assert result["total"] == 0
    assert result["items"] == []


def test_fts_matches_file_index_one_to_one(tmp_path):
    """设计属性 5：file_fts 匹配结果与 file_index 一一对应。"""
    db = _make_db(tmp_path)
    _seed(db)
    svc = FileQueryService(db)
    for q in ("会议纪要", "年度财务", "迭代计划"):
        result = svc.fts_query(q=q)
        with db.connect() as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM file_fts WHERE file_fts MATCH ?",
                ('"' + q + '"',),
            ).fetchone()["n"]
        assert result["total"] == n
        assert len(result["items"]) == min(n, 20)
