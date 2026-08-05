from sanic import Blueprint
from sanic.exceptions import NotFound
from sanic.response import ResponseStream, json, raw, text as text_response

from ..config import Config
from ..database import Database
from ..preview_service import PreviewError, PreviewService

_CHUNK = 64 * 1024


def create_preview_bp(db: Database, config: Config) -> Blueprint:
    bp = Blueprint("preview", url_prefix="/api/files")
    service = PreviewService(db, config)

    @bp.get("/<file_id:int>/preview")
    async def preview(request, file_id: int):
        record = service.files.get(file_id)
        if record is None:
            raise NotFound("file not found")
        rel_path = record.get("rel_path") or ""
        kind = service.kind(rel_path)

        if kind == "text":
            try:
                body, content_type = service.preview_text(file_id)
            except PreviewError as exc:
                return json({"error": str(exc)}, status=404)
            return text_response(body, content_type=content_type)

        if kind == "image":
            thumbnail = request.args.get("mode", "thumbnail") != "original"
            try:
                data, content_type = service.preview_image(file_id, thumbnail=thumbnail)
            except PreviewError as exc:
                return json({"error": str(exc)}, status=404)
            return raw(data, content_type=content_type)

        if kind == "pdf":
            try:
                pdf_stream, content_type = service.stream_pdf(file_id)
            except PreviewError as exc:
                return json({"error": str(exc)}, status=404)
            return ResponseStream(
                _stream_gzip(pdf_stream), content_type=content_type
            )

        return json({"error": "该文件类型暂不支持在线预览"}, status=415)

    return bp


def _stream_gzip(gz):
    async def streaming(response):
        try:
            while True:
                chunk = gz.read(_CHUNK)
                if not chunk:
                    break
                await response.write(chunk)
        finally:
            gz.close()

    return streaming
