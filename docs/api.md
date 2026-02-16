# API Draft

Base URL example: `https://api.example.com`

## Authentication
Required for:
- `POST /v1/pbs/generate`
- `POST /v1/license/validate`

Headers:
- `X-Client-Id`
- `X-Timestamp` (unix seconds)
- `X-Nonce` (random unique token)
- `X-Signature` (hex HMAC-SHA256)

Canonical string:
```text
METHOD\nPATH\nsha256(raw_body)\nX-Timestamp\nX-Nonce
```

## GET /health
No auth.

Response:
```json
{
  "ok": true,
  "redis": true
}
```

## POST /v1/pbs/generate
Request JSON:
```json
{
  "order_id": "857",
  "amount": "21.00",
  "currency": "EUR",
  "iban": "SK1583300000002503435769",
  "bic": "FIOZSKBAXXX",
  "recipient_name": "Zempres s.r.o.",
  "variable_symbol": "857",
  "message": "Platba za objednavku c.857",
  "due_date": "2026-02-19"
}
```

Response JSON:
```json
{
  "payload": "00088000....",
  "qr_svg": "<svg ...>...</svg>",
  "format": "pay_by_square"
}
```

## POST /v1/license/validate
DB-backed validation (HMAC protected).

Request JSON:
```json
{
  "license_key": "lic_xxxxxxxx",
  "domain": "shop.example.com",
  "plugin_instance_id": "wp_abc123456"
}
```

Response JSON:
```json
{
  "valid": true,
  "reason": ""
}
```

Validation rules:
- license exists
- status is `active`
- not expired
- domain matches (`*` works as wildcard)
- instance id matches if already bound

If `domain` / `plugin_instance_id` are empty in DB, they are bound on first successful validation.

## POST /v1/admin/license/upsert
Admin endpoint for simple license management.

Header:
- `X-Admin-Token`

Request JSON:
```json
{
  "license_key": "lic_12345678",
  "status": "active",
  "domain": "shop.example.com",
  "plugin_instance_id": "wp_abc123",
  "expires_at": "2026-12-31T23:59:59+00:00",
  "note": "customer #17"
}
```

Response:
```json
{
  "saved": true
}
```

## POST /v1/admin/client/upsert
Creates or updates API client metadata.

Header:
- `X-Admin-Token`

Request:
```json
{
  "client_id": "woo_prod",
  "status": "active",
  "note": "production wordpress plugin"
}
```

Response:
```json
{
  "client_id": "woo_prod",
  "status": "active",
  "note": "production wordpress plugin",
  "secret": ""
}
```

## POST /v1/admin/client/rotate-secret
Rotates client secret and returns the new value once.

Header:
- `X-Admin-Token`

Request:
```json
{
  "client_id": "woo_prod"
}
```

Response:
```json
{
  "client_id": "woo_prod",
  "status": "active",
  "note": "",
  "secret": "new_generated_secret_value"
}
```

## GET /v1/admin/audit/recent?limit=50
Returns latest audit records.

Header:
- `X-Admin-Token`

## GET /v1/admin/license/list?limit=100&q=
Returns recent licenses for admin UI.

Header:
- `X-Admin-Token`

## GET /admin
Browser UI with login + session cookie auth.

## POST /admin/api/login
Login for admin UI.
```json
{
  "username": "admin",
  "password": "secret",
  "otp_code": "123456"
}
```

## GET /admin/api/session
Returns active admin username from session cookie.

## POST /admin/api/logout
Ends admin session.

## GET /admin/api/license/list
Session-authenticated variant of license list for UI.

## POST /admin/api/license/upsert
Session-authenticated variant of license upsert for UI.

## GET /admin/api/user/list
Lists admin users (session auth).

## POST /admin/api/user/upsert
Creates/updates admin user account.
- supports active/inactive
- supports superadmin flag
- supports optional TOTP 2FA (`twofa_enabled`, `twofa_secret`)

## POST /admin/api/user/delete
Deletes admin user account (superadmin only, cannot delete current user).

## Error Codes
- `401`: invalid/missing auth, timestamp expired, nonce replay, invalid signature
- `422`: invalid request body
- `500`: generation failure
