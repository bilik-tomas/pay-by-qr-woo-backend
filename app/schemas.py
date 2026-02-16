from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PBSGenerateRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    iban: str = Field(min_length=10, max_length=34)
    bic: str = Field(default="", max_length=11)
    recipient_name: str = Field(default="", max_length=140)
    variable_symbol: str = Field(default="", max_length=20)
    message: str = Field(default="", max_length=140)
    due_date: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper().strip()

    @field_validator("iban")
    @classmethod
    def normalize_iban(cls, value: str) -> str:
        return value.replace(" ", "").upper().strip()

    @field_validator("bic")
    @classmethod
    def normalize_bic(cls, value: str) -> str:
        return value.replace(" ", "").upper().strip()


class PBSGenerateResponse(BaseModel):
    payload: str
    qr_svg: str
    format: str = "pay_by_square"


class LicenseValidateRequest(BaseModel):
    license_key: str = Field(min_length=8, max_length=128)
    domain: str = Field(min_length=3, max_length=255)
    plugin_instance_id: str = Field(min_length=6, max_length=128)


class LicenseValidateResponse(BaseModel):
    valid: bool
    reason: str = ""


class AdminLicenseUpsertRequest(BaseModel):
    license_key: str = Field(min_length=8, max_length=128)
    status: str = Field(default="active", min_length=4, max_length=16)
    domain: str = Field(default="", max_length=255)
    plugin_instance_id: str = Field(default="", max_length=128)
    expires_at: datetime | None = None
    note: str = Field(default="", max_length=255)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"active", "blocked", "expired"}:
            raise ValueError("invalid status")
        return normalized


class AdminLicenseUpsertResponse(BaseModel):
    saved: bool = True


class AdminLicenseItem(BaseModel):
    license_key: str
    status: str
    domain: str
    plugin_instance_id: str
    expires_at: datetime | None = None
    note: str
    created_at: datetime
    updated_at: datetime


class AdminLicenseListResponse(BaseModel):
    items: list[AdminLicenseItem]


class AdminClientUpsertRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=128)
    status: str = Field(default="active", min_length=4, max_length=16)
    note: str = Field(default="", max_length=255)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"active", "blocked"}:
            raise ValueError("invalid status")
        return normalized


class AdminClientRotateSecretRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=128)


class AdminClientResponse(BaseModel):
    client_id: str
    status: str
    note: str
    secret: str = ""


class AdminAuditLogItem(BaseModel):
    request_id: str
    client_id: str
    method: str
    path: str
    status_code: int
    latency_ms: int
    created_at: datetime
    error_detail: str = ""


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogItem]


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)
    otp_code: str = Field(default="", max_length=12)
    turnstile_token: str = Field(default="", max_length=4096)


class AdminLoginResponse(BaseModel):
    ok: bool = True
    username: str


class AdminSessionInfoResponse(BaseModel):
    username: str


class AdminLoginOptionsResponse(BaseModel):
    twofa_required: bool
    turnstile_required: bool
    turnstile_site_key: str = ""


class AdminUserItem(BaseModel):
    username: str
    is_active: bool
    is_superadmin: bool
    twofa_enabled: bool
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]


class AdminUserUpsertRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(default="", max_length=255)
    is_active: bool = True
    is_superadmin: bool = False
    twofa_enabled: bool = False
    twofa_secret: str = Field(default="", max_length=64)


class AdminUserDeleteRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)


class AdminLicenseDeleteRequest(BaseModel):
    license_key: str = Field(min_length=8, max_length=128)
