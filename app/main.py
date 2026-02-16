from datetime import datetime, timezone
from io import BytesIO
import json
import re
import time
import uuid
from urllib.parse import urlencode, urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

import secrets

import pyotp
import qrcode
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from qrcode.image.svg import SvgImage
from redis import Redis
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .admin_ui import ADMIN_HTML
from .admin_auth import (
    SESSION_COOKIE,
    admin_session_dep,
    issue_session_cookie,
    verify_password,
    verify_totp,
)
from .by_square import generate_payload, payload_to_svg
from .config import settings
from .db import SessionLocal, get_db
from .models import AdminUser, AuditLog, Client, License
from .schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLoginOptionsResponse,
    AdminSessionInfoResponse,
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminClientResponse,
    AdminClientRotateSecretRequest,
    AdminClientUpsertRequest,
    AdminLicenseItem,
    AdminLicenseListResponse,
    AdminLicenseDeleteRequest,
    AdminLicenseGenerateResponse,
    AdminLicenseUpsertRequest,
    AdminLicenseUpsertResponse,
    AdminTwoFaConfirmRequest,
    AdminTwoFaDisableRequest,
    AdminTwoFaStartResponse,
    AdminUserDeleteRequest,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserSetActiveRequest,
    AdminUserUpsertRequest,
    LicenseValidateRequest,
    LicenseValidateResponse,
    PBSGenerateRequest,
    PBSGenerateResponse,
)
from .security import AuthContext, generate_client_secret, verify_hmac

app = FastAPI(title="Pay By QR Woo Backend", version="0.1.0")
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_key(request: Request) -> str:
    # Limit by endpoint family and client IP.
    minute = int(time.time() // 60)
    ip = _client_ip(request)
    group = "other"
    if request.url.path.startswith("/v1/"):
        group = "v1"
    elif request.url.path.startswith("/admin/api/"):
        group = "admin"
    return f"rl:{group}:{ip}:{minute}"


def _normalize_domain(domain: str) -> str:
    value = domain.strip().lower()
    if not value:
        return ""
    if value in {"*", "*.*"}:
        return "*"
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.hostname or value
    host = host.split("/")[0].split(":")[0].strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def _domain_matches(stored_domain: str, request_domain: str) -> bool:
    normalized_request = _normalize_domain(request_domain)
    if not normalized_request:
        return False
    stored_raw = stored_domain.strip()
    if not stored_raw:
        return True
    candidates = [part.strip() for part in re.split(r"[,;\s]+", stored_raw) if part.strip()]
    for candidate in candidates:
        normalized = _normalize_domain(candidate)
        if not normalized:
            continue
        if normalized == "*":
            return True
        if normalized.startswith("*."):
            base = normalized[2:]
            if normalized_request == base or normalized_request.endswith(f".{base}"):
                return True
            continue
        if normalized_request == normalized:
            return True
    return False


def _normalize_domain_list(raw: str) -> str:
    parts = [part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()]
    if not parts:
        return ""
    normalized: list[str] = []
    for part in parts:
        item = _normalize_domain(part)
        if item and item not in normalized:
            normalized.append(item)
    return ",".join(normalized)


def _generate_license_key() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "-".join(groups)


def _qr_svg_from_text(payload: str) -> str:
    qr = qrcode.QRCode(border=2, box_size=7)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgImage)
    out = BytesIO()
    img.save(out)
    return out.getvalue().decode("utf-8")


def _pending_2fa_key(username: str) -> str:
    return f"admin:2fa:pending:{username}"


@app.middleware("http")
async def capture_body(request: Request, call_next):
    limited = request.url.path.startswith("/v1/") or request.url.path.startswith("/admin/api/")
    if limited and settings.rate_limit_per_minute > 0:
        key = _rate_limit_key(request)
        try:
            hits = int(redis_client.incr(key))
            if hits == 1:
                redis_client.expire(key, 70)
            if hits > settings.rate_limit_per_minute:
                return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        except Exception:
            # Fail-open on Redis errors to avoid false downtime.
            pass

    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    request.state.request_id = request_id
    body = await request.body()
    request.state.raw_body = body
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if request.url.path != "/health":
        try:
            with SessionLocal() as db:
                log = AuditLog(
                    request_id=request_id,
                    client_id=request.headers.get("X-Client-Id", "").strip(),
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    latency_ms=elapsed_ms,
                    remote_addr=(request.client.host if request.client else ""),
                    error_detail="",
                )
                db.add(log)
                db.commit()
        except Exception:
            pass
    response.headers["X-Request-Id"] = request_id
    return response


def _auth_dep(request: Request) -> AuthContext:
    return verify_hmac(request, redis_client)


def _admin_token_dep(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> None:
    expected = settings.admin_token.strip()
    provided = x_admin_token.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="admin token not configured")
    if not secrets.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="invalid admin token")


def _bootstrap_admin_from_env() -> None:
    username = settings.admin_username.strip()
    password_hash = settings.admin_password_hash.strip()
    if not username or not password_hash:
        return
    try:
        with SessionLocal() as db:
            row = db.scalar(select(AdminUser).where(AdminUser.username == username).limit(1))
            if not row:
                row = AdminUser(
                    username=username,
                    password_hash=password_hash,
                    is_active=1,
                    is_superadmin=1,
                )
            else:
                row.password_hash = password_hash
                row.is_active = 1
                row.is_superadmin = 1
            db.add(row)
            db.commit()
    except Exception:
        # Migration may not be applied yet on first boot.
        pass


def _is_turnstile_enabled() -> bool:
    return bool(settings.admin_turnstile_site_key.strip() and settings.admin_turnstile_secret_key.strip())


def _verify_turnstile_token(turnstile_token: str, remote_ip: str) -> bool:
    if not _is_turnstile_enabled():
        return True
    token = turnstile_token.strip()
    if not token:
        return False
    payload = urlencode(
        {
            "secret": settings.admin_turnstile_secret_key.strip(),
            "response": token,
            "remoteip": remote_ip,
        }
    ).encode("utf-8")
    req = UrlRequest(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False
    return bool(isinstance(data, dict) and data.get("success"))


@app.get("/health")
def health() -> dict:
    redis_ok = False
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False
    return {"ok": True, "redis": redis_ok}


@app.get("/admin", response_class=HTMLResponse)
def admin_page() -> str:
    return ADMIN_HTML


@app.on_event("startup")
def startup_bootstrap_admin() -> None:
    _bootstrap_admin_from_env()


@app.post("/admin/api/login", response_model=AdminLoginResponse)
def admin_api_login(
    payload: AdminLoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> AdminLoginResponse:
    if _is_turnstile_enabled():
        remote_ip = request.client.host if request.client else ""
        if not _verify_turnstile_token(payload.turnstile_token, remote_ip):
            raise HTTPException(status_code=401, detail="turnstile verification failed")
    row = db.scalar(select(AdminUser).where(AdminUser.username == payload.username).limit(1))
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail="invalid credentials")
    try:
        password_ok = verify_password(payload.password, row.password_hash)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid credentials") from exc
    if not password_ok:
        raise HTTPException(status_code=401, detail="invalid credentials")
    if row.twofa_enabled:
        try:
            otp_ok = verify_totp(row.twofa_secret, payload.otp_code)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="invalid otp code") from exc
        if not otp_ok:
            raise HTTPException(status_code=401, detail="invalid otp code")
    token = issue_session_cookie(row.username)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=(request.url.scheme == "https"),
        samesite="lax",
        max_age=12 * 60 * 60,
    )
    return AdminLoginResponse(ok=True, username=row.username)


@app.get("/admin/api/login/options", response_model=AdminLoginOptionsResponse)
def admin_api_login_options(username: str = "", db: Session = Depends(get_db)) -> AdminLoginOptionsResponse:
    user = db.scalar(select(AdminUser).where(AdminUser.username == username.strip()).limit(1))
    return AdminLoginOptionsResponse(
        twofa_required=bool(user and user.is_active and user.twofa_enabled),
        turnstile_required=_is_turnstile_enabled(),
        turnstile_site_key=settings.admin_turnstile_site_key.strip() if _is_turnstile_enabled() else "",
    )


@app.post("/admin/api/logout")
def admin_api_logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/admin/api/session", response_model=AdminSessionInfoResponse)
def admin_api_session(session=Depends(admin_session_dep)) -> AdminSessionInfoResponse:
    return AdminSessionInfoResponse(username=session.username)


@app.post("/admin/api/license/generate", response_model=AdminLicenseGenerateResponse)
def admin_api_license_generate(_=Depends(admin_session_dep)) -> AdminLicenseGenerateResponse:
    return AdminLicenseGenerateResponse(license_key=_generate_license_key())


@app.get("/admin/api/license/list", response_model=AdminLicenseListResponse)
def admin_api_license_list(
    q: str = "",
    limit: int = 100,
    _=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> AdminLicenseListResponse:
    return admin_license_list(q=q, limit=limit, _=None, db=db)


@app.post("/admin/api/license/upsert", response_model=AdminLicenseUpsertResponse)
def admin_api_license_upsert(
    payload: AdminLicenseUpsertRequest,
    _=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> AdminLicenseUpsertResponse:
    return admin_license_upsert(payload=payload, _=None, db=db)


@app.post("/admin/api/license/delete")
def admin_api_license_delete(
    payload: AdminLicenseDeleteRequest,
    _=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(select(License).where(License.license_key == payload.license_key).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/admin/api/user/list", response_model=AdminUserListResponse)
def admin_api_user_list(_=Depends(admin_session_dep), db: Session = Depends(get_db)) -> AdminUserListResponse:
    rows = db.scalars(select(AdminUser).order_by(AdminUser.username.asc())).all()
    return AdminUserListResponse(
        items=[
            AdminUserItem(
                username=row.username,
                is_active=bool(row.is_active),
                is_superadmin=bool(row.is_superadmin),
                twofa_enabled=bool(row.twofa_enabled),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )


@app.post("/admin/api/user/upsert")
def admin_api_user_upsert(
    payload: AdminUserUpsertRequest,
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    current = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not current or not current.is_superadmin:
        raise HTTPException(status_code=403, detail="superadmin required")

    row = db.scalar(select(AdminUser).where(AdminUser.username == payload.username).limit(1))
    if not row:
        if not payload.password:
            raise HTTPException(status_code=400, detail="password required for new user")
        row = AdminUser(username=payload.username, password_hash=settings.admin_password_hash or "")
    if payload.password:
        from .admin_auth import hash_password

        row.password_hash = hash_password(payload.password)
    row.is_active = 1 if payload.is_active else 0
    row.is_superadmin = 1 if payload.is_superadmin else 0
    row.twofa_enabled = 1 if payload.twofa_enabled else 0
    if payload.twofa_enabled:
        row.twofa_secret = payload.twofa_secret.strip() or pyotp.random_base32()
    else:
        row.twofa_secret = ""
    db.add(row)
    db.commit()
    return {"ok": True}


@app.post("/admin/api/user/set-active")
def admin_api_user_set_active(
    payload: AdminUserSetActiveRequest,
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    current = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not current or not current.is_superadmin:
        raise HTTPException(status_code=403, detail="superadmin required")
    row = db.scalar(select(AdminUser).where(AdminUser.username == payload.username).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if row.username == session.username and not payload.is_active:
        raise HTTPException(status_code=400, detail="cannot disable current user")
    row.is_active = 1 if payload.is_active else 0
    db.add(row)
    db.commit()
    return {"ok": True}


@app.post("/admin/api/user/2fa/start", response_model=AdminTwoFaStartResponse)
def admin_api_user_2fa_start(
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> AdminTwoFaStartResponse:
    row = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail="admin account inactive")
    secret = pyotp.random_base32()
    issuer = "PayByQR Woo Backend"
    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=row.username, issuer_name=issuer)
    redis_client.setex(_pending_2fa_key(row.username), 10 * 60, secret)
    return AdminTwoFaStartResponse(
        secret=secret,
        otpauth_url=otpauth_url,
        qr_svg=_qr_svg_from_text(otpauth_url),
    )


@app.post("/admin/api/user/2fa/confirm")
def admin_api_user_2fa_confirm(
    payload: AdminTwoFaConfirmRequest,
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    secret = redis_client.get(_pending_2fa_key(row.username)) or ""
    if not secret:
        raise HTTPException(status_code=400, detail="2fa setup expired, start again")
    if not verify_totp(secret, payload.otp_code):
        raise HTTPException(status_code=400, detail="invalid otp code")
    row.twofa_enabled = 1
    row.twofa_secret = secret
    db.add(row)
    db.commit()
    redis_client.delete(_pending_2fa_key(row.username))
    return {"ok": True}


@app.post("/admin/api/user/2fa/disable")
def admin_api_user_2fa_disable(
    payload: AdminTwoFaDisableRequest,
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if row.twofa_enabled and not verify_totp(row.twofa_secret, payload.otp_code):
        raise HTTPException(status_code=400, detail="invalid otp code")
    row.twofa_enabled = 0
    row.twofa_secret = ""
    db.add(row)
    db.commit()
    redis_client.delete(_pending_2fa_key(row.username))
    return {"ok": True}


@app.post("/admin/api/user/delete")
def admin_api_user_delete(
    payload: AdminUserDeleteRequest,
    session=Depends(admin_session_dep),
    db: Session = Depends(get_db),
) -> dict:
    current = db.scalar(select(AdminUser).where(AdminUser.username == session.username).limit(1))
    if not current or not current.is_superadmin:
        raise HTTPException(status_code=403, detail="superadmin required")
    if payload.username == session.username:
        raise HTTPException(status_code=400, detail="cannot delete current user")
    row = db.scalar(select(AdminUser).where(AdminUser.username == payload.username).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.post("/v1/pbs/generate", response_model=PBSGenerateResponse)
def pbs_generate(
    payload: PBSGenerateRequest,
    auth: AuthContext = Depends(_auth_dep),
) -> PBSGenerateResponse:
    del auth
    try:
        pbs_payload = generate_payload(payload)
        qr_svg = payload_to_svg(pbs_payload)
        return PBSGenerateResponse(payload=pbs_payload, qr_svg=qr_svg)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"generation failed: {exc}") from exc


@app.post("/v1/license/validate", response_model=LicenseValidateResponse)
def license_validate(
    payload: LicenseValidateRequest,
    auth: AuthContext = Depends(_auth_dep),
    db: Session = Depends(get_db),
) -> LicenseValidateResponse:
    del auth
    license_row = db.scalar(
        select(License).where(License.license_key == payload.license_key).limit(1)
    )
    if not license_row:
        return LicenseValidateResponse(valid=False, reason="invalid license")

    if license_row.status != "active":
        return LicenseValidateResponse(valid=False, reason="license not active")

    if license_row.expires_at and license_row.expires_at < datetime.now(timezone.utc):
        return LicenseValidateResponse(valid=False, reason="license expired")

    requested_domain = _normalize_domain(payload.domain)
    if not _domain_matches(license_row.domain, requested_domain):
        return LicenseValidateResponse(valid=False, reason="domain mismatch")

    if license_row.plugin_instance_id and license_row.plugin_instance_id != payload.plugin_instance_id:
        return LicenseValidateResponse(valid=False, reason="instance mismatch")

    changed = False
    if not license_row.domain:
        license_row.domain = requested_domain
        changed = True
    if not license_row.plugin_instance_id:
        license_row.plugin_instance_id = payload.plugin_instance_id
        changed = True
    if changed:
        db.add(license_row)
        db.commit()

    return LicenseValidateResponse(valid=True)


@app.post("/v1/admin/license/upsert", response_model=AdminLicenseUpsertResponse)
def admin_license_upsert(
    payload: AdminLicenseUpsertRequest,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> AdminLicenseUpsertResponse:
    license_row = db.scalar(
        select(License).where(License.license_key == payload.license_key).limit(1)
    )
    if not license_row:
        license_row = License(license_key=payload.license_key)

    license_row.status = payload.status
    license_row.domain = _normalize_domain_list(payload.domain)
    license_row.plugin_instance_id = payload.plugin_instance_id
    license_row.expires_at = payload.expires_at
    license_row.note = payload.note
    db.add(license_row)
    db.commit()

    return AdminLicenseUpsertResponse(saved=True)


@app.get("/v1/admin/license/list", response_model=AdminLicenseListResponse)
def admin_license_list(
    q: str = "",
    limit: int = 100,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> AdminLicenseListResponse:
    safe_limit = max(1, min(500, limit))
    stmt = select(License).order_by(desc(License.updated_at)).limit(safe_limit)
    query = q.strip().lower()
    rows = db.scalars(stmt).all()
    if query:
        rows = [
            row
            for row in rows
            if query in row.license_key.lower()
            or query in row.domain.lower()
            or query in row.note.lower()
        ]
    return AdminLicenseListResponse(
        items=[
            AdminLicenseItem(
                license_key=row.license_key,
                status=row.status,
                domain=row.domain,
                plugin_instance_id=row.plugin_instance_id,
                expires_at=row.expires_at,
                note=row.note,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )


@app.post("/v1/admin/license/delete")
def admin_license_delete(
    payload: AdminLicenseDeleteRequest,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> dict:
    row = db.scalar(select(License).where(License.license_key == payload.license_key).limit(1))
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.post("/v1/admin/license/generate", response_model=AdminLicenseGenerateResponse)
def admin_license_generate(_: None = Depends(_admin_token_dep)) -> AdminLicenseGenerateResponse:
    return AdminLicenseGenerateResponse(license_key=_generate_license_key())


@app.post("/v1/admin/client/upsert", response_model=AdminClientResponse)
def admin_client_upsert(
    payload: AdminClientUpsertRequest,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> AdminClientResponse:
    row = db.scalar(select(Client).where(Client.client_id == payload.client_id).limit(1))
    if not row:
        row = Client(client_id=payload.client_id, secret_value=generate_client_secret())
    row.status = payload.status
    row.note = payload.note
    db.add(row)
    db.commit()
    return AdminClientResponse(
        client_id=row.client_id,
        status=row.status,
        note=row.note,
    )


@app.post("/v1/admin/client/rotate-secret", response_model=AdminClientResponse)
def admin_client_rotate_secret(
    payload: AdminClientRotateSecretRequest,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> AdminClientResponse:
    row = db.scalar(select(Client).where(Client.client_id == payload.client_id).limit(1))
    if not row:
        row = Client(client_id=payload.client_id, status="active", note="")
    new_secret = generate_client_secret()
    row.secret_value = new_secret
    db.add(row)
    db.commit()
    return AdminClientResponse(
        client_id=row.client_id,
        status=row.status,
        note=row.note,
        secret=new_secret,
    )


@app.get("/v1/admin/audit/recent", response_model=AdminAuditLogListResponse)
def admin_audit_recent(
    limit: int = 50,
    _: None = Depends(_admin_token_dep),
    db: Session = Depends(get_db),
) -> AdminAuditLogListResponse:
    safe_limit = max(1, min(200, limit))
    rows = db.scalars(
        select(AuditLog).order_by(desc(AuditLog.created_at)).limit(safe_limit)
    ).all()
    return AdminAuditLogListResponse(
        items=[
            AdminAuditLogItem(
                request_id=row.request_id,
                client_id=row.client_id,
                method=row.method,
                path=row.path,
                status_code=row.status_code,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
                error_detail=row.error_detail,
            )
            for row in rows
        ]
    )
