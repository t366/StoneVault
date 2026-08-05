import asyncio

from app.config import Config
from app.database import Database
from app.repositories import SnapshotRepository, TaskRepository
from app.scheduler.locks import TaskExecutionManager
from app.scheduler.scheduler import TaskScheduler


def _make_db(tmp_path) -> Database:
    db = Database(tmp_path / "db.sqlite")
    db.initialize()
    return db


async def test_execution_manager_merges_concurrent_triggers(tmp_path):
    db = _make_db(tmp_path)
    task_id = TaskRepository(db).create(
        name="t", source_path="/tmp/x", hdd_rel_path="t"
    )
    manager = TaskExecutionManager(db)
    runs = []

    async def slow_run():
        runs.append("start")
        await asyncio.sleep(0.05)
        runs.append("end")

    first = asyncio.create_task(manager.execute(task_id, slow_run))
    await asyncio.sleep(0.01)
    second = asyncio.create_task(manager.execute(task_id, slow_run))
    results = await asyncio.gather(first, second)

    assert results == [True, False]
    assert runs == ["start", "end"]

    snapshots = SnapshotRepository(db).list_by_task(task_id)
    assert len(snapshots) == 1
    assert snapshots[0]["status"] == "skipped"
    assert "合并" in snapshots[0]["error_message"]


async def test_execution_manager_serializes_different_tasks(tmp_path):
    db = _make_db(tmp_path)
    repo = TaskRepository(db)
    task_a = repo.create(name="a", source_path="/tmp/a", hdd_rel_path="a")
    task_b = repo.create(name="b", source_path="/tmp/b", hdd_rel_path="b")
    manager = TaskExecutionManager(db, interleave_seconds=0)
    order = []

    async def run():
        order.append("start")
        await asyncio.sleep(0.03)
        order.append("end")

    await asyncio.gather(
        manager.execute(task_a, run),
        manager.execute(task_b, run),
    )
    assert order == ["start", "end", "start", "end"]


def test_resync_registers_cron_jobs(tmp_path):
    db = _make_db(tmp_path)
    repo = TaskRepository(db)
    cron_id = repo.create(
        name="cron",
        source_path="/tmp/c",
        hdd_rel_path="c",
        schedule_cron="0 2 * * *",
        enabled=1,
    )
    manual_id = repo.create(
        name="manual", source_path="/tmp/m", hdd_rel_path="m", enabled=1
    )
    disabled_id = repo.create(
        name="disabled",
        source_path="/tmp/d",
        hdd_rel_path="d",
        schedule_cron="0 3 * * *",
        enabled=0,
    )
    bad_cron_id = repo.create(
        name="bad",
        source_path="/tmp/b",
        hdd_rel_path="b",
        schedule_cron="not a valid cron",
        enabled=1,
    )

    scheduler = TaskScheduler(
        db, engine=None, manager=TaskExecutionManager(db), config=Config()
    )
    scheduler.resync()

    jobs = scheduler.scheduler.get_jobs()
    job_ids = {job.id for job in jobs}
    assert job_ids == {f"task-{cron_id}"}
    assert f"task-{manual_id}" not in job_ids
    assert f"task-{disabled_id}" not in job_ids
    assert f"task-{bad_cron_id}" not in job_ids

    scheduler.shutdown()
