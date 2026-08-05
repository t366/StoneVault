from pathlib import Path

from sanic import Blueprint
from sanic.exceptions import NotFound
from sanic.response import file_stream, json

from ..database import Database
from ..repositories import FileIndexRepository
from ..wake_manager import WakeManager


def create_download_bp(db: Database, wake_manager: WakeManager) -> Blueprint:
    bp = Blueprint("download", url_prefix="/api/files")
    files = FileIndexRepository(db)

    @bp.get("/<file_id:int>/download")
    async def download(request, file_id: int):
        record = files.get(file_id)
        if record is None:
            raise NotFound("file not found")
        hdd_path = record.get("hdd_source_path")
        if not wake_manager.is_mounted():
            return json(
                {"error": "冷区硬盘离线，无法下载源文件，请检查硬盘连接"},
                status=503,
            )
        if not hdd_path or not Path(hdd_path).is_file():
            return json(
                {"error": "冷区源文件不存在，请检查硬盘挂载"}, status=404
            )
        if not await wake_manager.acquire():
            return json(
                {"error": "冷区唤醒超时，请稍后重试"}, status=503
            )
        try:
            return await file_stream(
                hdd_path,
                filename=record.get("filename") or Path(hdd_path).name,
            )
        finally:
            wake_manager.release()

    return bp
