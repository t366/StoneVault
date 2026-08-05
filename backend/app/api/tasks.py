import asyncio

from sanic import Blueprint
from sanic.exceptions import NotFound
from sanic.response import json

from ..backup_engine.engine import BackupEngine
from ..config import Config
from ..database import Database
from ..repositories import SnapshotRepository, TaskRepository
from ..scheduler.locks import TaskExecutionManager
from ..scheduler.scheduler import TaskScheduler

VALID_MODES = {"full", "incremental"}


def _validate_payload(data: dict) -> tuple[dict, str | None]:
    errors: dict[str, str] = {}
    name = str(data.get("name") or "").strip()
    source_path = str(data.get("source_path") or "").strip()
    hdd_rel_path = str(data.get("hdd_rel_path") or "").strip()
    if not name:
        errors["name"] = "任务名称不能为空"
    if not source_path:
        errors["source_path"] = "源目录不能为空"
    if not hdd_rel_path:
        errors["hdd_rel_path"] = "冷区目标相对路径不能为空"

    mode = data.get("backup_mode", "full")
    if mode not in VALID_MODES:
        errors["backup_mode"] = "备份模式仅支持 full / incremental"

    min_size = data.get("filter_min_size")
    max_size = data.get("filter_max_size")
    if min_size is not None and (not isinstance(min_size, int) or min_size < 0):
        errors["filter_min_size"] = "大小下限必须为非负整数"
    if max_size is not None and (not isinstance(max_size, int) or max_size < 0):
        errors["filter_max_size"] = "大小上限必须为非负整数"
    if (
        min_size is not None
        and max_size is not None
        and isinstance(min_size, int)
        and isinstance(max_size, int)
        and min_size > max_size
    ):
        errors["filter_min_size"] = "大小下限不能大于上限"

    extensions = data.get("filter_extensions")
    if extensions is not None and not isinstance(extensions, list):
        errors["filter_extensions"] = "扩展名过滤必须为数组"

    payload = {
        "name": name,
        "source_path": source_path,
        "hdd_rel_path": hdd_rel_path,
        "schedule_cron": (str(data.get("schedule_cron") or "").strip() or None),
        "filter_extensions": extensions,
        "filter_min_size": min_size,
        "filter_max_size": max_size,
        "backup_mode": mode,
        "enabled": 1 if data.get("enabled", True) else 0,
    }
    if errors:
        return payload, "；".join(f"{k}: {v}" for k, v in errors.items())
    return payload, None


def create_tasks_bp(
    db: Database,
    engine: BackupEngine,
    manager: TaskExecutionManager,
    scheduler: TaskScheduler,
    config: Config,
) -> Blueprint:
    bp = Blueprint("tasks", url_prefix="/api/tasks")
    tasks = TaskRepository(db)
    snapshots = SnapshotRepository(db)

    def _resync() -> None:
        scheduler.resync()

    @bp.get("/")
    async def list_tasks(request):
        return json({"items": tasks.list()})

    @bp.post("/")
    async def create_task(request):
        data = request.json or {}
        payload, error = _validate_payload(data)
        if error:
            return json({"error": error}, status=400)
        task_id = tasks.create(**payload)
        _resync()
        return json({"id": task_id, **tasks.get(task_id)}, status=201)

    @bp.get("/<task_id:int>")
    async def get_task(request, task_id: int):
        task = tasks.get(task_id)
        if task is None:
            raise NotFound("task not found")
        return json(task)

    @bp.put("/<task_id:int>")
    async def update_task(request, task_id: int):
        if tasks.get(task_id) is None:
            raise NotFound("task not found")
        data = request.json or {}
        payload, error = _validate_payload(data)
        if error:
            return json({"error": error}, status=400)
        tasks.update(task_id, **payload)
        _resync()
        return json(tasks.get(task_id))

    @bp.delete("/<task_id:int>")
    async def delete_task(request, task_id: int):
        if tasks.get(task_id) is None:
            raise NotFound("task not found")
        tasks.delete(task_id)
        _resync()
        return json({"ok": True})

    @bp.post("/<task_id:int>/run")
    async def run_task(request, task_id: int):
        if tasks.get(task_id) is None:
            raise NotFound("task not found")
        triggered = await manager.execute(
            task_id,
            lambda: asyncio.to_thread(
                engine.run_task, task_id, config.BACKUP_RATE_LIMIT
            ),
        )
        if not triggered:
            return json(
                {
                    "triggered": False,
                    "status": "skipped",
                    "reason": "任务仍在运行，本次触发已合并为跳过",
                }
            )
        return json({"triggered": True, "status": "success"})

    @bp.get("/<task_id:int>/logs")
    async def task_logs(request, task_id: int):
        if tasks.get(task_id) is None:
            raise NotFound("task not found")
        return json({"items": snapshots.list_by_task(task_id)})

    return bp
