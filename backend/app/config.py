from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass
class Config:
    HOST: str = os.environ.get("STONEVAULT_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("STONEVAULT_PORT", "8000"))

    DATA_DIR: Path = Path(os.environ.get("STONEVAULT_DATA_DIR", "/var/lib/stonevault"))
    HDD_MOUNT_PATH: Path = Path(os.environ.get("STONEVAULT_HDD_MOUNT", "/mnt/backup"))

    SESSION_TTL_SECONDS: int = int(os.environ.get("STONEVAULT_SESSION_TTL", "86400"))
    SECRET_KEY: str = os.environ.get("STONEVAULT_SECRET_KEY", "dev-secret-change-me")
    ADMIN_USERNAME: str = os.environ.get("STONEVAULT_ADMIN_USERNAME", "")
    ADMIN_PASSWORD: str = os.environ.get("STONEVAULT_ADMIN_PASSWORD", "")
    AI_MAX_CONCURRENCY: int = int(os.environ.get("STONEVAULT_AI_CONCURRENCY", "2"))
    TRANSCODE_MAX_CONCURRENCY: int = int(
        os.environ.get("STONEVAULT_TRANSCODE_CONCURRENCY", "1")
    )
    WAKE_TIMEOUT_SECONDS: int = int(os.environ.get("STONEVAULT_WAKE_TIMEOUT", "30"))
    WAKE_DEBOUNCE_SECONDS: int = int(os.environ.get("STONEVAULT_WAKE_DEBOUNCE", "10"))
    BACKUP_RATE_LIMIT: int = int(os.environ.get("STONEVAULT_BACKUP_RATE", "0"))
    SCHEDULE_TIMEZONE: str = os.environ.get("STONEVAULT_SCHEDULE_TZ", "Asia/Shanghai")
    TASK_INTERLEAVE_SECONDS: int = int(os.environ.get("STONEVAULT_TASK_INTERLEAVE", "30"))

    db_path: Path = field(init=False)
    ssd_cache_dir: Path = field(init=False)
    ssd_thumb_dir: Path = field(init=False)
    ssd_tmp_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.db_path = self.DATA_DIR / "stonevault.db"
        self.ssd_cache_dir = self.DATA_DIR / "cache"
        self.ssd_thumb_dir = self.DATA_DIR / "thumbs"
        self.ssd_tmp_dir = self.DATA_DIR / "tmp"

    def ensure_dirs(self) -> None:
        for path in (self.DATA_DIR, self.ssd_cache_dir, self.ssd_thumb_dir, self.ssd_tmp_dir):
            path.mkdir(parents=True, exist_ok=True)


default_config = Config()
