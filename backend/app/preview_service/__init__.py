import gzip
import io
import mimetypes
from pathlib import Path

from PIL import Image

from ..config import Config
from ..database import Database
from ..repositories import FileIndexRepository

_TEXT_EXTS = {".txt", ".md", ".log", ".csv", ".json", ".xml", ".yaml", ".yml", ".ini", ".conf"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
_PDF_EXTS = {".pdf"}
_TEXT_LIMIT = 512 * 1024
_THUMBNAIL_SIZE = 512


class PreviewError(Exception):
    pass


def _ext_from_path(rel_path: str) -> str:
    return Path(rel_path).suffix.lower()


class PreviewService:
    """在线预览服务：仅从热区缓存副本读取，不触发冷区唤醒（需求 6.4）。"""

    def __init__(self, db: Database, config: Config) -> None:
        self.db = db
        self.config = config
        self.files = FileIndexRepository(db)

    def kind(self, rel_path: str) -> str:
        ext = _ext_from_path(rel_path)
        if ext in _IMAGE_EXTS:
            return "image"
        if ext in _PDF_EXTS:
            return "pdf"
        if ext in _TEXT_EXTS:
            return "text"
        return "unsupported"

    def _cache_path(self, file_id: int) -> Path:
        record = self.files.get(file_id)
        if record is None:
            raise PreviewError("文件不存在")
        cache = record.get("ssd_cache_path")
        if not cache:
            raise PreviewError("热区无缓存副本")
        path = Path(cache)
        if not path.exists():
            raise PreviewError("热区缓存副本缺失")
        return path

    def _open_cache(self, file_id: int) -> gzip.GzipFile:
        path = self._cache_path(file_id)
        return gzip.open(path, "rb")

    def _read_raw(self, file_id: int) -> bytes:
        with self._open_cache(file_id) as f:
            return f.read()

    def preview_text(self, file_id: int) -> tuple[str, str]:
        data = self._read_raw(file_id)
        text = _decode_text(data)
        if len(data) > _TEXT_LIMIT:
            text = text[:_TEXT_LIMIT] + "\n\n[内容过长，仅预览前 512KB]"
        return text, "text/plain; charset=utf-8"

    def preview_image(self, file_id: int, thumbnail: bool = True) -> tuple[bytes, str]:
        if thumbnail:
            thumb_path = self.config.ssd_thumb_dir / f"{file_id}.jpg"
            if not thumb_path.exists():
                self._make_thumbnail(file_id, thumb_path)
            return thumb_path.read_bytes(), "image/jpeg"
        record = self.files.get(file_id)
        if record is None:
            raise PreviewError("文件不存在")
        content_type = mimetypes.guess_type(record.get("rel_path") or "")[0] or "application/octet-stream"
        return self._read_raw(file_id), content_type

    def _make_thumbnail(self, file_id: int, dst: Path) -> None:
        data = self._read_raw(file_id)
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.thumbnail((_THUMBNAIL_SIZE, _THUMBNAIL_SIZE))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
        except Exception as exc:
            raise PreviewError(f"图片无法解析: {exc}") from exc
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(buf.getvalue())

    def stream_pdf(self, file_id: int) -> tuple[gzip.GzipFile, str]:
        record = self.files.get(file_id)
        if record is None:
            raise PreviewError("文件不存在")
        content_type = mimetypes.guess_type(record.get("rel_path") or "")[0] or "application/pdf"
        return self._open_cache(file_id), content_type


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
