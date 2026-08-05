from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Config
from app.database import Database
from app.repositories import FileIndexRepository, SnapshotRepository, TaskRepository
from app.query_service import FileQueryService
from app.server import create_app


def _make_db(tmp_path) -> Database:
    db = Database(tmp_path / "db.sqlite")
    db.initialize()
    return db


def _seed(db: Database, n: int = 30, prefix: str = "report") -> int:
    repo = TaskRepository(db)
    snapshots = SnapshotRepository(db)
    files = FileIndexRepository(db)
    task_id = repo.create(name="t", source_path="/src", hdd_rel_path="t")
    snapshot_id = snapshots.create(
        task_id=task_id,
        started_at="2026-08-01T10:00:00",
        status="success",
    )
    for i in range(n):
        ext = ".txt" if i % 3 == 0 else (".jpg" if i % 3 == 1 else ".pdf")
        files.create(
            snapshot_id=snapshot_id,
            rel_path=f"docs/{prefix}_{i}{ext}",
            file_size=100 + i,
            filename=f"{prefix}_{i}{ext}",
            body="",
            ai_text="",
        )
    return snapshot_id


def test_pagination(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30)
    svc = FileQueryService(db)
    result = svc.query(page=1, page_size=10)
    assert result["total"] == 30
    assert len(result["items"]) == 10
    assert result["page"] == 1

    page3 = svc.query(page=3, page_size=10)
    assert len(page3["items"]) == 10
    ids1 = {it["id"] for it in result["items"]}
    ids3 = {it["id"] for it in page3["items"]}
    assert ids1.isdisjoint(ids3)


def test_pagination_bounds(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=5)
    svc = FileQueryService(db)
    result = svc.query(page=0, page_size=100000)
    assert result["page"] == 1
    assert result["page_size"] == 200


def test_filename_filter(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30, prefix="annual")
    svc = FileQueryService(db)
    result = svc.query(q="annual_2")
    assert 0 < result["total"] <= 11
    assert all("annual_2" in it["filename"] for it in result["items"])


def test_ext_filter(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30)
    svc = FileQueryService(db)
    result = svc.query(ext="jpg")
    assert result["total"] == 10
    assert all(it["rel_path"].endswith(".jpg") for it in result["items"])

    result_no_dot = svc.query(ext=".txt")
    assert result_no_dot["total"] == 10


def test_size_range(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30)
    svc = FileQueryService(db)
    result = svc.query(size_min=110, size_max=119)
    ids = {it["id"] for it in result["items"]}
    assert all(110 <= it["file_size"] <= 119 for it in result["items"])
    assert len(ids) == 10


def test_time_range(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30)
    svc = FileQueryService(db)
    result = svc.query(from_time="2026-08-01")
    assert result["total"] == 30
    empty = svc.query(from_time="2027-01-01")
    assert empty["total"] == 0
    window = svc.query(to_time="2026-07-31")
    assert window["total"] == 0


def test_combined_filters(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=30)
    svc = FileQueryService(db)
    result = svc.query(ext="txt", size_min=100, size_max=200, page_size=5)
    assert all(
        it["rel_path"].endswith(".txt") and 100 <= it["file_size"] <= 200
        for it in result["items"]
    )
    assert result["total"] == 10


def test_sorting(tmp_path):
    db = _make_db(tmp_path)
    _seed(db, n=10)
    svc = FileQueryService(db)
    asc = svc.query(sort_by="file_size", order="asc")
    sizes = [it["file_size"] for it in asc["items"]]
    assert sizes == sorted(sizes)
    desc = svc.query(sort_by="file_size", order="desc")
    assert [it["file_size"] for it in desc["items"]] == sorted(sizes, reverse=True)


@pytest.fixture
def app(tmp_path: Path):
    cfg = Config(
        DATA_DIR=tmp_path / "data",
        HDD_MOUNT_PATH=tmp_path / "hdd",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="secret",
    )
    cfg.ensure_dirs()
    return create_app(cfg, name=f"stonevault-files-{uuid4().hex}")


def test_files_api_flow(app):
    _seed(app.ctx.db, n=6)
    _, login = app.test_client.post(
        "/api/auth/login", json={"username": "admin", "password": "secret"}
    )
    token = login.json["token"]
    headers = {"Authorization": f"Bearer {token}"}

    _, resp = app.test_client.get("/api/files/?ext=pdf&page=1&page_size=2", headers=headers)
    assert resp.status == 200
    body = resp.json
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert all(it["rel_path"].endswith(".pdf") for it in body["items"])

    _, resp = app.test_client.get("/api/files/?size_min=abc", headers=headers)
    assert resp.status == 400
