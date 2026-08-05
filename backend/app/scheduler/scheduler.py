import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..backup_engine.engine import BackupEngine
from ..config import Config
from ..database import Database
from ..repositories import TaskRepository
from .locks import TaskExecutionManager

_MAX_INSTANCES = 1
_MISFIRE_GRACE_SECONDS = 300


class TaskScheduler:
    """APScheduler 集成：按任务 Cron 表达式触发备份，并共享执行锁。

    - 启用且配置了 schedule_cron 的任务注册为 cron 作业（需求 3.1）。
    - 触发时经 TaskExecutionManager 执行，保证幂等与错峰（需求 3.3、3.4）。
    """

    def __init__(
        self,
        db: Database,
        engine: BackupEngine,
        manager: TaskExecutionManager,
        config: Config,
    ) -> None:
        self.db = db
        self.engine = engine
        self.manager = manager
        self.config = config
        self.tasks = TaskRepository(db)
        self._scheduler = AsyncIOScheduler(timezone=config.SCHEDULE_TIMEZONE)

    @property
    def scheduler(self) -> AsyncIOScheduler:
        return self._scheduler

    def resync(self) -> None:
        """根据数据库中的任务配置重建 cron 作业。"""
        self._scheduler.remove_all_jobs()
        for task in self.tasks.list():
            cron = (task.get("schedule_cron") or "").strip()
            if not cron or not task.get("enabled"):
                continue
            try:
                trigger = CronTrigger.from_crontab(cron)
            except ValueError:
                continue
            self._scheduler.add_job(
                self._job,
                trigger,
                args=[task["id"]],
                id=f"task-{task['id']}",
                replace_existing=True,
                max_instances=_MAX_INSTANCES,
                coalesce=True,
                misfire_grace_time=_MISFIRE_GRACE_SECONDS,
            )

    def start(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._scheduler = AsyncIOScheduler(timezone=self.config.SCHEDULE_TIMEZONE)
        self.resync()
        self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def _job(self, task_id: int) -> None:
        task = self.tasks.get(task_id)
        if task is None or not task.get("enabled"):
            return
        await self.manager.execute(
            task_id,
            lambda: asyncio.to_thread(
                self.engine.run_task,
                task_id,
                self.config.BACKUP_RATE_LIMIT,
            ),
        )
