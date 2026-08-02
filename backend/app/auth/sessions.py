import base64
import hashlib
import hmac
import json
import time


class SessionManager:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self.secret = secret.encode("utf-8")
        self.ttl = ttl_seconds

    def create_token(self, username: str) -> str:
        payload = json.dumps(
            {"sub": username, "exp": int(time.time()) + self.ttl},
            separators=(",", ":"),
        ).encode("utf-8")
        body = base64.urlsafe_b64encode(payload).rstrip(b"=")
        signature = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        return f"{body.decode('ascii')}.{signature}"

    def verify_token(self, token: str) -> str | None:
        try:
            body_b64, signature = token.split(".")
            body = base64.urlsafe_b64decode(
                body_b64 + "=" * (-len(body_b64) % 4)
            )
            payload = json.loads(body)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        expected = hmac.new(self.secret, body_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload.get("sub")
