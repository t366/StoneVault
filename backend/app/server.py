from sanic import Sanic
from sanic.response import json

from .api.auth import create_auth_bp
from .auth.middleware import register_auth_middleware
from .auth.passwords import hash_password
from .auth.sessions import SessionManager
from .config import Config, default_config
from .database import Database
from .repositories import AdminUserRepository


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

    @app.get("/api/health")
    async def health(request):
        return json(
            {
                "status": "ok",
                "service": "stonevault",
                "hdd_mounted": str(cfg.HDD_MOUNT_PATH).startswith("/"),
            }
        )

    app.blueprint(create_auth_bp(database, sessions))
    register_auth_middleware(app, sessions)
    return app


def main() -> None:
    app = create_app()
    app.run(host=app.config.HOST, port=app.config.PORT, workers=1, access_log=True)


if __name__ == "__main__":
    main()
