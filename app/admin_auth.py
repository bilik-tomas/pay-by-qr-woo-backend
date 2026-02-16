from __future__ import annotations

from dataclasses import dataclass

import pyotp
from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import AdminUser

SESSION_COOKIE = "pbs_admin_session"
SESSION_TTL_SECONDS = 12 * 60 * 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class AdminSession:
    username: str


def _serializer() -> URLSafeTimedSerializer:
    secret = settings.admin_session_secret.strip() or settings.admin_token.strip()
    if not secret:
        raise HTTPException(status_code=503, detail="admin session secret not configured")
    return URLSafeTimedSerializer(secret_key=secret, salt="pbs-admin-session")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(code.strip(), valid_window=1))


def issue_session_cookie(username: str) -> str:
    token = _serializer().dumps({"username": username})
    return token


def parse_session_cookie(raw_cookie: str) -> AdminSession:
    try:
        data = _serializer().loads(raw_cookie, max_age=SESSION_TTL_SECONDS)
    except SignatureExpired as exc:
        raise HTTPException(status_code=401, detail="admin session expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="invalid admin session") from exc

    username = str(data.get("username", "")).strip()
    if not username:
        raise HTTPException(status_code=401, detail="invalid admin session")
    return AdminSession(username=username)


def admin_session_dep(
    db: Session = Depends(get_db),
    pbs_admin_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> AdminSession:
    if not pbs_admin_session:
        raise HTTPException(status_code=401, detail="admin login required")

    session = parse_session_cookie(pbs_admin_session)
    row = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail="admin account inactive")
    return session
