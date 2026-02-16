# Architecture Proposal

## 1. Scope
This backend serves the WooCommerce plugin for:
- generating valid Pay by Square payloads and QR SVG
- validating plugin license keys
- providing controlled API access using per-client HMAC credentials

Expected traffic: ~20 QR generations/day (very low), with architecture still ready for bursts and abuse protection.

## 2. Runtime Components
- `api` (FastAPI): business logic, auth, payload/QR generation
- `redis`: nonce storage for replay protection and short-lived auth state
- `db` (PostgreSQL): client credentials, licenses, audit log (next phase)
- host reverse proxy (`apache` or `nginx`): TLS termination, request filtering, proxy to `127.0.0.1:8080`
- optional `Cloudflare`: edge WAF/rate-limits/DDoS protection

## 3. Request Security Model
All state-changing/business endpoints require HMAC headers:
- `X-Client-Id`
- `X-Timestamp` (unix seconds)
- `X-Nonce` (single use within TTL)
- `X-Signature` (HMAC-SHA256)

Canonical payload signed by plugin:
`METHOD + "\n" + PATH + "\n" + sha256(raw_body) + "\n" + TIMESTAMP + "\n" + NONCE`

Validation flow:
1. check known client id
2. check timestamp within TTL (default 300s)
3. check nonce not reused (Redis `SETEX`)
4. compare signatures using constant-time compare

## 4. License Admin Model (Plugin Side)
Plugin settings should include:
- API endpoint URL
- client id
- client secret
- license key

Recommended workflow:
1. Admin saves settings in WP
2. Plugin sends signed request to `/v1/license/validate`
3. Backend responds with `valid=true/false` and reason
4. Plugin stores status and checks periodically (daily WP-Cron)

## 5. DDoS and Abuse Controls
Minimum controls without external services:
- bind API only to localhost
- allow traffic only through nginx
- nginx `limit_req` + `limit_conn`
- small body limit (`client_max_body_size 64k`)
- fail2ban for repeated 401/429/5xx patterns

With Cloudflare (optional):
- WAF rules by path (`/v1/*`)
- managed bot protection
- per-IP request rate policies

## 6. Data Model (next step)
- `clients`: `id`, `client_id`, `secret_value`, `status`, `created_at`
- `licenses`: `id`, `license_key`, `domain`, `plugin_instance_id`, `status`, `expires_at`
- `audit_logs`: `id`, `request_id`, `client_id`, `path`, `http_status`, `created_at`

## 7. Why This Design
Pros:
- simple deploy on one VPS
- strong request authentication without OAuth overhead
- no external paid dependency required

Cons:
- requires secure secret handling in WP plugin
- replay protection depends on Redis availability
- no automatic key rotation yet (add in next phase)
