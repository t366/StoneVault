from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Config
from app.server import create_app


@pytest.fixture
def app(tmp_path: Path):
    cfg = Config(DATA_DIR=tmp_path / "data", HDD_MOUNT_PATH=tmp_path / "hdd")
    cfg.ensure_dirs()
    return create_app(cfg, name=f"stonevault-test-{uuid4().hex}")


def test_app_creation(app):
    assert app.name.startswith("stonevault-test-")
    assert app.config["PORT"] == 8000


def test_health_endpoint(app):
    request, response = app.test_client.get("/api/health")
    assert response.status == 200
    body = response.json
    assert body["status"] == "ok"
    assert body["service"] == "stonevault"
