from sanic import Sanic
from sanic.response import json

from .api.auth import create_auth_bp
from .api.download import create_download_bp
from .api.files import create_files_bp
from .api.preview import create_preview_bp
from .api.tasks import create_tasks_bp
from .auth.middleware import register_auth_middleware
from .auth.passwords import hash_password
from .auth.sessions import SessionManager
from .backup_engine.engine import BackupEngine
from .config import Config, default_config
from .database import Database
from .repositories import AdminUserRepository
from .scheduler.locks import TaskExecutionManager
from .scheduler.scheduler import TaskScheduler
from .wake_manager import WakeController, WakeManager


def create_app(
    config: Config | None = None,
    name: str = "StoneVault",
    db: Database | None = None,
    session_manager: SessionManager | None = None,
) -> Sanic:
    cfg = config or default_config
    app = Sanic(name)
    app.config.update(vars(cfg))
    app.ctx.config = cfg

    database = db or Database(cfg.db_path)
    database.initialize()
    app.ctx.db = database

    if cfg.ADMIN_PASSWORD and cfg.ADMIN_USERNAME:
        admin_repo = AdminUserRepository(database)
        if admin_repo.get_by_username(cfg.ADMIN_USERNAME) is None:
            admin_repo.create(
                username=cfg.ADMIN_USERNAME,
                password_hash=hash_password(cfg.ADMIN_PASSWORD),
            )

    sessions = session_manager or SessionManager(cfg.SECRET_KEY, cfg.SESSION_TTL_SECONDS)
    app.ctx.sessions = sessions

    engine = BackupEngine(database, cfg)
    manager = TaskExecutionManager(database, cfg.TASK_INTERLEAVE_SECONDS)
    scheduler = TaskScheduler(database, engine, manager, cfg)
    wake_controller = WakeController(cfg.HDD_MOUNT_PATH)
    wake_manager = WakeManager(
        wake_controller,
        debounce_seconds=cfg.WAKE_DEBOUNCE_SECONDS,
        timeout_seconds=cfg.WAKE_TIMEOUT_SECONDS,
    )
    app.ctx.engine = engine
    app.ctx.manager = manager
    app.ctx.scheduler = scheduler
    app.ctx.wake_manager = wake_manager

    @app.get("/api/health")
    async def health(request):
        return json(
            {
                "status": "ok",
                "service": "stonevault",
                "hdd_mounted": str(cfg.HDD_MOUNT_PATH).startswith("/"),
            }
        )

    @app.listener("after_server_start")
    async def start_scheduler(app_instance, loop):
        scheduler.resync()
        scheduler.start()

    @app.listener("before_server_stop")
    async def stop_scheduler(app_instance, loop):
        scheduler.shutdown()

    app.blueprint(create_auth_bp(database, sessions))
    app.blueprint(
        create_tasks_bp(database, engine, manager, scheduler, cfg)
    )
    app.blueprint(create_files_bp(database))
    app.blueprint(create_preview_bp(database, cfg))
    app.blueprint(create_download_bp(database, wake_manager))
    register_auth_middleware(app, sessions)
    return app


def main() -> None:
    app = create_app()
    app.run(
        host=app.config.HOST,
        port=app.config.PORT,
        workers=1,
        access_log=True,
        single_process=True,
    )


if __name__ == "__main__":
    main()
