from sanic import Blueprint
from sanic.exceptions import Unauthorized
from sanic.response import json

from ..auth.passwords import verify_password
from ..auth.sessions import SessionManager
from ..database import Database
from ..repositories import AdminUserRepository

PUBLIC = {"/api/auth/login"}


def create_auth_bp(db: Database, session_manager: SessionManager) -> Blueprint:
    bp = Blueprint("auth", url_prefix="/api/auth")

    @bp.post("/login")
    async def login(request):
        data = request.json or {}
        username = str(data.get("username") or "")
        password = str(data.get("password") or "")
        admin = AdminUserRepository(db).get_by_username(username)
        if admin is None or not verify_password(password, admin["password_hash"]):
            raise Unauthorized("invalid credentials")
        return json({"token": session_manager.create_token(username), "username": username})

    @bp.post("/logout")
    async def logout(request):
        return json({"ok": True})

    return bp
