from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Config
from app.server import create_app


@pytest.fixture
def app(tmp_path: Path):
    cfg = Config(
        DATA_DIR=tmp_path / "data",
        HDD_MOUNT_PATH=tmp_path / "hdd",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="secret",
        BACKUP_RATE_LIMIT=0,
        TASK_INTERLEAVE_SECONDS=0,
    )
    cfg.ensure_dirs()
    return create_app(cfg, name=f"stonevault-tasks-{uuid4().hex}")


@pytest.fixture
def token(app):
    _, resp = app.test_client.post(
        "/api/auth/login", json={"username": "admin", "password": "secret"}
    )
    assert resp.status == 200
    return resp.json["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_tasks_require_auth(app):
    _, resp = app.test_client.get("/api/tasks/")
    assert resp.status == 401


def test_create_task_validation(app, token):
    h = _auth(token)
    _, resp = app.test_client.post("/api/tasks/", json={}, headers=h)
    assert resp.status == 400
    error = resp.json["error"]
    assert "任务名称" in error and "源目录" in error

    _, resp = app.test_client.post(
        "/api/tasks/",
        json={
            "name": "t",
            "source_path": "/tmp",
            "hdd_rel_path": "t",
            "backup_mode": "weird",
            "filter_extensions": "not-a-list",
        },
        headers=h,
    )
    assert resp.status == 400
    assert "backup_mode" in resp.json["error"]
    assert "filter_extensions" in resp.json["error"]


def test_crud_flow(app, token):
    h = _auth(token)
    payload = {
        "name": "照片备份",
        "source_path": "/data/photos",
        "hdd_rel_path": "photos",
        "schedule_cron": "0 2 * * *",
        "filter_extensions": [".jpg", ".png"],
        "filter_min_size": 1024,
        "backup_mode": "incremental",
    }
    _, resp = app.test_client.post("/api/tasks/", json=payload, headers=h)
    assert resp.status == 201
    body = resp.json
    task_id = body["id"]
    assert body["name"] == "照片备份"
    assert body["backup_mode"] == "incremental"
    assert body["filter_extensions"] == [".jpg", ".png"]
    assert body["enabled"] == 1

    _, resp = app.test_client.get(f"/api/tasks/{task_id}", headers=h)
    assert resp.status == 200
    assert resp.json["source_path"] == "/data/photos"

    _, resp = app.test_client.get("/api/tasks/", headers=h)
    assert resp.status == 200
    assert len(resp.json["items"]) == 1

    _, resp = app.test_client.put(
        f"/api/tasks/{task_id}",
        json={**payload, "name": "新名称", "enabled": False},
        headers=h,
    )
    assert resp.status == 200
    assert resp.json["name"] == "新名称"
    assert resp.json["enabled"] == 0

    _, resp = app.test_client.delete(f"/api/tasks/{task_id}", headers=h)
    assert resp.status == 200
    _, resp = app.test_client.get(f"/api/tasks/{task_id}", headers=h)
    assert resp.status == 404


def test_run_task_success(app, token, tmp_path):
    h = _auth(token)
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello stonevault")

    _, resp = app.test_client.post(
        "/api/tasks/",
        json={"name": "t", "source_path": str(src), "hdd_rel_path": "t"},
        headers=h,
    )
    task_id = resp.json["id"]

    _, resp = app.test_client.post(f"/api/tasks/{task_id}/run", headers=h)
    assert resp.status == 200
    assert resp.json["triggered"] is True

    hdd_file = tmp_path / "hdd" / "t" / "a.txt"
    assert hdd_file.exists()
    assert hdd_file.read_text() == "hello stonevault"

    from app.repositories import SnapshotRepository

    snapshots = SnapshotRepository(app.ctx.db).list_by_task(task_id)
    assert snapshots[0]["status"] == "success"
    assert snapshots[0]["file_count"] == 1

    _, resp = app.test_client.get(f"/api/tasks/{task_id}/logs", headers=h)
    assert resp.status == 200
    assert len(resp.json["items"]) == 1


def test_run_missing_task(app, token):
    h = _auth(token)
    _, resp = app.test_client.post("/api/tasks/99999/run", headers=h)
    assert resp.status == 404
