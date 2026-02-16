#!/usr/bin/env python3
"""Runtime smoke test for local API."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8080")
CLIENT_ID = os.getenv("CLIENT_ID", "woo_smoke")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change_me_admin_token")


def request_json(path: str, method: str = "GET", headers: dict | None = None, payload: dict | None = None):
    body = b""
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body if method != "GET" else None,
        method=method,
        headers=headers or {},
    )
    if payload is not None and "Content-Type" not in req.headers:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def sign_headers(method: str, path: str, body_obj: dict, client_secret: str) -> tuple[dict, bytes]:
    body = json.dumps(body_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ts = str(int(time.time()))
    nonce = secrets.token_hex(12)
    body_sha = hashlib.sha256(body).hexdigest()
    canonical = "\n".join([method.upper(), path, body_sha, ts, nonce])
    if not client_secret:
        raise RuntimeError("CLIENT_SECRET missing for signed request")
    signature = hmac.new(client_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Client-Id": CLIENT_ID,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }
    return headers, body


def request_signed(path: str, payload: dict, client_secret: str):
    headers, body = sign_headers("POST", path, payload, client_secret)
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    client_secret = CLIENT_SECRET
    status, body = request_json("/health")
    print("health:", status, body)

    status, body = request_json(
        "/v1/admin/license/upsert",
        method="POST",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        payload={
            "license_key": "lic_demo_123456",
            "status": "active",
            "domain": "shop.example.com",
            "plugin_instance_id": "",
            "note": "smoke test",
        },
    )
    print("admin upsert:", status, body)

    status, body = request_json(
        "/v1/admin/client/upsert",
        method="POST",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        payload={"client_id": CLIENT_ID, "status": "active", "note": "smoke test"},
    )
    print("client upsert:", status, body)

    status, body = request_json(
        "/v1/admin/client/rotate-secret",
        method="POST",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        payload={"client_id": CLIENT_ID},
    )
    print("client rotate-secret:", status, {"client_id": body.get("client_id"), "status": body.get("status")})
    if status == 200 and body.get("secret"):
        client_secret = body["secret"]

    status, body = request_signed(
        "/v1/license/validate",
        {
            "license_key": "lic_demo_123456",
            "domain": "shop.example.com",
            "plugin_instance_id": "wp_test_001",
        },
        client_secret=client_secret,
    )
    print("license validate:", status, body)

    status, body = request_signed(
        "/v1/pbs/generate",
        {
            "order_id": "857",
            "amount": "21.00",
            "currency": "EUR",
            "iban": "SK1583300000002503435769",
            "bic": "FIOZSKBAXXX",
            "recipient_name": "Zempres s.r.o.",
            "variable_symbol": "857",
            "message": "Platba za objednavku c.857",
            "due_date": "2026-02-19",
        },
        client_secret=client_secret,
    )
    qr_len = len(body.get("qr_svg", "")) if isinstance(body, dict) else 0
    print("pbs generate:", status, {"format": body.get("format"), "qr_svg_len": qr_len})

    status, body = request_json(
        "/v1/admin/audit/recent?limit=5",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    print("audit recent:", status, {"count": len(body.get("items", [])) if isinstance(body, dict) else 0})

    status, body = request_json(
        "/v1/admin/license/list?limit=5",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    print("license list:", status, {"count": len(body.get("items", [])) if isinstance(body, dict) else 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
