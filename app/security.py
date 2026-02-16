import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from redis import Redis
from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Client


@dataclass(frozen=True)
class AuthContext:
    client_id: str


def generate_client_secret() -> str:
    return secrets.token_urlsafe(36)


def _get_db_secret_value(client_id: str) -> str:
    with SessionLocal() as db:
        row = db.scalar(
            select(Client)
            .where(Client.client_id == client_id)
            .where(Client.status == "active")
            .limit(1)
        )
        if not row:
            return ""
        return row.secret_value


def _parse_clients() -> dict[str, str]:
    result: dict[str, str] = {}
    raw = settings.api_clients.strip()
    if not raw:
        return result

    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        client_id, secret = pair.split(":", 1)
        result[client_id.strip()] = secret.strip()
    return result


def _canonical(method: str, path: str, body: bytes, ts: str, nonce: str) -> str:
    body_sha = hashlib.sha256(body).hexdigest()
    return "\n".join([method.upper(), path, body_sha, ts, nonce])


def verify_hmac(
    request: Request,
    redis_client: Redis,
) -> AuthContext:
    x_client_id = request.headers.get("X-Client-Id", "").strip()
    x_timestamp = request.headers.get("X-Timestamp", "").strip()
    x_nonce = request.headers.get("X-Nonce", "").strip()
    x_signature = request.headers.get("X-Signature", "").strip()

    env_clients = _parse_clients()
    env_secret = env_clients.get(x_client_id, "")
    db_secret = _get_db_secret_value(x_client_id)
    if not env_secret and not db_secret:
        raise HTTPException(status_code=401, detail="invalid client")

    try:
        ts = int(x_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="invalid timestamp") from exc

    now = int(time.time())
    if abs(now - ts) > settings.api_sign_ttl_seconds:
        raise HTTPException(status_code=401, detail="timestamp expired")

    if not x_nonce:
        raise HTTPException(status_code=401, detail="missing nonce")

    nonce_key = f"auth_nonce:{x_client_id}:{x_nonce}"
    if redis_client.get(nonce_key):
        raise HTTPException(status_code=401, detail="replay detected")

    body = getattr(request.state, "raw_body", b"")
    canonical = _canonical(request.method, request.url.path, body, x_timestamp, x_nonce)
    valid_signature = False
    if env_secret:
        expected = hmac.new(
            env_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        valid_signature = hmac.compare_digest(expected, x_signature)

    if not valid_signature and db_secret:
        expected = hmac.new(
            db_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        valid_signature = hmac.compare_digest(expected, x_signature)

    if not valid_signature:
        raise HTTPException(status_code=401, detail="invalid signature")

    redis_client.setex(nonce_key, settings.api_sign_ttl_seconds, "1")
    return AuthContext(client_id=x_client_id)
