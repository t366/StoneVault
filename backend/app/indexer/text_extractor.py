import gzip
import re
import zipfile
from pathlib import Path

from ..preview_service import _decode_text

_TEXT_EXTS = {
    ".txt", ".md", ".log", ".csv", ".json", ".xml", ".yaml", ".yml",
    ".ini", ".conf", ".html", ".htm", ".css", ".js", ".py", ".sh",
}
_PDF_EXTS = {".pdf"}
_DOCX_EXTS = {".docx"}
_MAX_TEXT_BYTES = 8 * 1024 * 1024

_W_TAG = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.DOTALL)


def extract_text(cache_path: Path, rel_path: str) -> str:
    """从热区 gzip 缓存副本提取文档正文，供 FTS5 索引。"""
    suffix = rel_path.rsplit(".", 1)[-1].lower() if "." in rel_path else ""
    ext = f".{suffix}"
    if ext in _PDF_EXTS:
        return _extract_pdf(cache_path)
    if ext in _DOCX_EXTS:
        return _extract_docx(cache_path)
    if ext in _TEXT_EXTS:
        return _extract_plain(cache_path)
    return ""


def _read_cache(cache_path: Path, limit: int = _MAX_TEXT_BYTES) -> bytes:
    with gzip.open(cache_path, "rb") as f:
        return f.read(limit)


def _extract_plain(cache_path: Path) -> str:
    try:
        return _decode_text(_read_cache(cache_path))
    except OSError:
        return ""


def _extract_pdf(cache_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        with gzip.open(cache_path, "rb") as f:
            reader = PdfReader(f)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
    except Exception:
        return ""


def _extract_docx(cache_path: Path) -> str:
    try:
        with gzip.open(cache_path, "rb") as f:
            data = f.read()
    except OSError:
        return ""
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
            document = zf.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError):
        return ""
    paragraphs = []
    for xml_block in document.split("</w:p>"):
        text = "".join(_W_TAG.findall(xml_block))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)
