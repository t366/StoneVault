from sanic import Sanic
from sanic.exceptions import Unauthorized

from .sessions import SessionManager

PUBLIC_PATHS = {"/api/health", "/api/auth/login"}


def register_auth_middleware(app: Sanic, session_manager: SessionManager) -> None:
    @app.middleware("request")
    async def enforce_auth(request):
        path = request.path
        if path in PUBLIC_PATHS or not path.startswith("/api"):
            return
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise Unauthorized("authentication required")
        username = session_manager.verify_token(auth_header[7:])
        if username is None:
            raise Unauthorized("invalid or expired session")
        request.ctx.username = username
