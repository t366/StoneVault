import gzip
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..database import Database
from ..repositories import FileIndexRepository, SnapshotRepository, TaskRepository
from .filtering import FilterSpec


def md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def write_gzip_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open("rb") as fin, gzip.open(dst, "wb") as fout:
        shutil.copyfileobj(fin, fout)


class BackupEngine:
    def __init__(self, db: Database, config: Config) -> None:
        self.db = db
        self.config = config
        self.tasks = TaskRepository(db)
        self.snapshots = SnapshotRepository(db)
        self.files = FileIndexRepository(db)

    def run_task(self, task_id: int) -> dict:
        task = self.tasks.get(task_id)
        if task is None:
            raise ValueError(f"task {task_id} not found")
        source = Path(task["source_path"])
        hdd_base = self.config.HDD_MOUNT_PATH / task["hdd_rel_path"]
        snapshot_id = self.snapshots.create(
            task_id=task_id,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        spec = FilterSpec(
            extensions=task["filter_extensions"],
            min_size=task["filter_min_size"],
            max_size=task["filter_max_size"],
        )
        mode = task["backup_mode"]
        try:
            file_count = 0
            total_bytes = 0
            for path in self._scan(source, spec):
                rel = path.relative_to(source)
                if mode == "incremental" and self._unchanged(rel, path, task_id):
                    continue
                file_count += 1
                total_bytes += path.stat().st_size
                self._backup_file(snapshot_id, rel, path, hdd_base)
            self.snapshots.finish(
                snapshot_id,
                status="success",
                file_count=file_count,
                total_bytes=total_bytes,
            )
        except Exception as exc:
            self.snapshots.finish(snapshot_id, status="failed", error_message=str(exc))
            raise
        return self.snapshots.get(snapshot_id)

    def _scan(self, source: Path, spec: FilterSpec) -> list[Path]:
        if not source.is_dir():
            return []
        result = []
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            size = path.stat().st_size
            if spec.matches(path, size):
                result.append(path)
        return result

    def _unchanged(self, rel: Path, path: Path, task_id: int) -> bool:
        prev = self.files.find_by_rel_path(str(rel), task_id=task_id)
        if prev is None:
            return False
        if prev["mtime"] != str(path.stat().st_mtime):
            return False
        return prev["md5"] == md5_file(path)

    def _backup_file(self, snapshot_id: int, rel: Path, src: Path, hdd_base: Path) -> None:
        st = src.stat()
        hdd_path = hdd_base / rel
        copy_file(src, hdd_path)
        digest = md5_file(src)
        cache_path = self.config.ssd_cache_dir / f"{snapshot_id}-{rel.name}.gz"
        write_gzip_copy(src, cache_path)
        self.files.create(
            snapshot_id=snapshot_id,
            rel_path=str(rel),
            file_size=st.st_size,
            md5=digest,
            mtime=str(st.st_mtime),
            ssd_cache_path=str(cache_path),
            hdd_source_path=str(hdd_path),
            filename=rel.name,
        )
