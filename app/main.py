from datetime import datetime, timezone
import time
import uuid

import secrets

import pyotp
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
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
    AdminSessionInfoResponse,
    AdminAuditLogItem,
    AdminAuditLogListResponse,
    AdminClientResponse,
    AdminClientRotateSecretRequest,
    AdminClientUpsertRequest,
    AdminLicenseItem,
    AdminLicenseListResponse,
    AdminLicenseUpsertRequest,
    AdminLicenseUpsertResponse,
    AdminUserDeleteRequest,
    AdminUserItem,
    AdminUserListResponse,
    AdminUserUpsertRequest,
    LicenseValidateRequest,
    LicenseValidateResponse,
    PBSGenerateRequest,
    PBSGenerateResponse,
)
from .security import AuthContext, generate_client_secret, verify_hmac

app = FastAPI(title="Pay By QR Woo Backend", version="0.1.0")
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


@app.middleware("http")
async def capture_body(request: Request, call_next):
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
def admin_api_login(payload: AdminLoginRequest, response: Response, db: Session = Depends(get_db)) -> AdminLoginResponse:
    row = db.scalar(select(AdminUser).where(AdminUser.username == payload.username).limit(1))
    if not row or not row.is_active:
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if row.twofa_enabled:
        if not verify_totp(row.twofa_secret, payload.otp_code):
            raise HTTPException(status_code=401, detail="invalid otp code")
    token = issue_session_cookie(row.username)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=12 * 60 * 60,
    )
    return AdminLoginResponse(ok=True, username=row.username)


@app.post("/admin/api/logout")
def admin_api_logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/admin/api/session", response_model=AdminSessionInfoResponse)
def admin_api_session(session=Depends(admin_session_dep)) -> AdminSessionInfoResponse:
    return AdminSessionInfoResponse(username=session.username)


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

    if license_row.domain and license_row.domain != "*" and license_row.domain != payload.domain:
        return LicenseValidateResponse(valid=False, reason="domain mismatch")

    if license_row.plugin_instance_id and license_row.plugin_instance_id != payload.plugin_instance_id:
        return LicenseValidateResponse(valid=False, reason="instance mismatch")

    changed = False
    if not license_row.domain:
        license_row.domain = payload.domain
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
    license_row.domain = payload.domain
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
