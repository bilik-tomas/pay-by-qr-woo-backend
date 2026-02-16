#!/usr/bin/env python3
"""Helper to create HMAC headers for backend requests."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import time


def build_canonical(method: str, path: str, body: bytes, ts: str, nonce: str) -> str:
    body_sha = hashlib.sha256(body).hexdigest()
    return "\n".join([method.upper(), path, body_sha, ts, nonce])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HMAC headers for API call.")
    parser.add_argument("--method", default="POST")
    parser.add_argument("--path", default="/v1/pbs/generate")
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument(
        "--body",
        default='{"order_id":"123","amount":"21.50","currency":"EUR","iban":"SK123","bic":"","variable_symbol":"123","message":"Test"}',
    )
    args = parser.parse_args()

    # Keep body stable to match hash used by the API.
    body_obj = json.loads(args.body)
    body_json = json.dumps(body_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    ts = str(int(time.time()))
    nonce = secrets.token_hex(12)
    canonical = build_canonical(args.method, args.path, body_json, ts, nonce)
    signature = hmac.new(
        args.client_secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    print("Body:")
    print(body_json.decode("utf-8"))
    print()
    print("Headers:")
    print(f"X-Client-Id: {args.client_id}")
    print(f"X-Timestamp: {ts}")
    print(f"X-Nonce: {nonce}")
    print(f"X-Signature: {signature}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
