import asyncio
import inspect
from datetime import datetime

from ..database import Database
from ..repositories import SnapshotRepository


class TaskExecutionManager:
    """任务执行锁与幂等触发。

    每个任务持有独立异步锁：同一任务并发触发时后到者被合并为单次，
    并写入一条 status='skipped' 的快照记录原因（需求 3.4 / 正确性属性 6）。
    所有备份任务经全局串行锁错峰执行，任务间可配置间隔（需求 3.3）。
    """

    def __init__(self, db: Database, interleave_seconds: float = 0.0) -> None:
        self.db = db
        self.snapshots = SnapshotRepository(db)
        self._locks: dict[int, asyncio.Lock] = {}
        self._serial = asyncio.Lock()
        self.interleave_seconds = interleave_seconds

    def _lock_for(self, task_id: int) -> asyncio.Lock:
        lock = self._locks.get(task_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[task_id] = lock
        return lock

    def is_running(self, task_id: int) -> bool:
        lock = self._locks.get(task_id)
        return lock is not None and lock.locked()

    async def execute(self, task_id: int, func, *args, **kwargs) -> bool:
        """执行任务；冲突触发返回 False 并记录 skipped 快照。"""
        lock = self._lock_for(task_id)
        if lock.locked():
            self._mark_skipped(task_id, "任务仍在运行，本次触发已合并为跳过")
            return False
        async with lock:
            async with self._serial:
                result = func(*args, **kwargs)
                if inspect.isawaitable(result):
                    await result
            if self.interleave_seconds > 0:
                await asyncio.sleep(self.interleave_seconds)
        return True

    def _mark_skipped(self, task_id: int, reason: str) -> None:
        snapshot_id = self.snapshots.create(
            task_id=task_id,
            started_at=datetime.now().isoformat(timespec="seconds"),
            status="skipped",
        )
        self.snapshots.finish(
            snapshot_id, status="skipped", error_message=reason
        )
