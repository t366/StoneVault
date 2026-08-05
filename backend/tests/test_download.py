from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Config
from app.repositories import FileIndexRepository, SnapshotRepository, TaskRepository
from app.server import create_app


@pytest.fixture
def ctx(tmp_path: Path):
    cfg = Config(
        DATA_DIR=tmp_path / "data",
        HDD_MOUNT_PATH=tmp_path / "hdd",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="secret",
    )
    cfg.ensure_dirs()
    (tmp_path / "hdd").mkdir(parents=True, exist_ok=True)
    app = create_app(cfg, name=f"sv-download-{uuid4().hex}")
    _, login = app.test_client.post(
        "/api/auth/login", json={"username": "admin", "password": "secret"}
    )
    headers = {"Authorization": f"Bearer {login.json['token']}"}
    return app, cfg, headers


def _seed_with_hdd(ctx, name: str, content: bytes):
    app, cfg, _ = ctx
    task_id = TaskRepository(app.ctx.db).create(
        name="t", source_path="/s", hdd_rel_path="t"
    )
    snap_id = SnapshotRepository(app.ctx.db).create(
        task_id=task_id, started_at="2026-08-01T10:00:00", status="success"
    )
    hdd_path = cfg.HDD_MOUNT_PATH / "t" / name
    hdd_path.parent.mkdir(parents=True, exist_ok=True)
    hdd_path.write_bytes(content)
    file_id = FileIndexRepository(app.ctx.db).create(
        snapshot_id=snap_id,
        rel_path=f"docs/{name}",
        file_size=len(content),
        ssd_cache_path="",
        hdd_source_path=str(hdd_path),
        filename=name,
    )
    return file_id


def test_download_streams_hdd_file(ctx):
    app, _, headers = ctx
    file_id = _seed_with_hdd(ctx, "raw.bin", b"\x00\x01\x02stonevault-data")
    _, resp = app.test_client.get(f"/api/files/{file_id}/download", headers=headers)
    assert resp.status == 200
    assert resp.body == b"\x00\x01\x02stonevault-data"
    assert resp.headers.get("Content-Disposition", "").find("raw.bin") >= 0


def test_download_missing_hdd_file_404(ctx):
    app, cfg, headers = ctx
    task_id = TaskRepository(app.ctx.db).create(name="t", source_path="/s", hdd_rel_path="t")
    snap_id = SnapshotRepository(app.ctx.db).create(
        task_id=task_id, started_at="2026-08-01T10:00:00", status="success"
    )
    file_id = FileIndexRepository(app.ctx.db).create(
        snapshot_id=snap_id,
        rel_path="docs/nope.bin",
        file_size=3,
        hdd_source_path=str(cfg.HDD_MOUNT_PATH / "t" / "nope.bin"),
        filename="nope.bin",
    )
    _, resp = app.test_client.get(f"/api/files/{file_id}/download", headers=headers)
    assert resp.status == 404


def test_download_offline_hdd_503(tmp_path):
    cfg = Config(
        DATA_DIR=tmp_path / "data",
        HDD_MOUNT_PATH=tmp_path / "missing-hdd",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="secret",
    )
    cfg.ensure_dirs()
    app = create_app(cfg, name=f"sv-dl-offline-{uuid4().hex}")
    _, login = app.test_client.post(
        "/api/auth/login", json={"username": "admin", "password": "secret"}
    )
    headers = {"Authorization": f"Bearer {login.json['token']}"}

    task_id = TaskRepository(app.ctx.db).create(name="t", source_path="/s", hdd_rel_path="t")
    snap_id = SnapshotRepository(app.ctx.db).create(
        task_id=task_id, started_at="2026-08-01T10:00:00", status="success"
    )
    file_id = FileIndexRepository(app.ctx.db).create(
        snapshot_id=snap_id,
        rel_path="docs/x.bin",
        file_size=3,
        hdd_source_path=str(tmp_path / "missing-hdd" / "t" / "x.bin"),
        filename="x.bin",
    )
    _, resp = app.test_client.get(f"/api/files/{file_id}/download", headers=headers)
    assert resp.status == 503
    assert "离线" in resp.json["error"]


def test_download_requires_auth(ctx):
    app, _, _ = ctx
    _, resp = app.test_client.get("/api/files/1/download")
    assert resp.status == 401
