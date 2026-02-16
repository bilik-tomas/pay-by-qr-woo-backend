# Pay By QR Woo Backend

API backend for WooCommerce plugin integration with Pay by Square (BY SQUARE).

## What This Service Does
- Generates Pay by Square payload string server-side
- Generates QR code as SVG from that payload
- Protects endpoints with HMAC signatures
- Provides initial license validation endpoint for plugin admin

## Stack
- Python 3.12
- FastAPI + Uvicorn
- Redis (nonce replay protection)
- PostgreSQL (prepared for license/client persistence)
- Docker Compose

## Repository Layout
- `app/main.py`: FastAPI app and routes
- `app/security.py`: HMAC verification and anti-replay logic
- `app/by_square.py`: Payload + QR generation
- `app/schemas.py`: Request/response models and normalization
- `docs/`: architecture, API and VPS runbook
- `scripts/example_sign_request.py`: helper to generate signed headers

## Quick Start (Local)
1. Create env:
```bash
cp .env.example .env
```
2. Set a real `API_CLIENTS` secret in `.env`.
3. Start:
```bash
docker compose up -d --build
```
4. Verify:
```bash
docker compose ps
curl -s http://127.0.0.1:8080/health
```

## Endpoint Summary
- `GET /health`
- `POST /v1/pbs/generate` (HMAC required)
- `POST /v1/license/validate` (HMAC required)
- `POST /v1/admin/license/upsert` (X-Admin-Token required)
- `GET /v1/admin/license/list` (X-Admin-Token required)
- `POST /v1/admin/client/upsert` (X-Admin-Token required)
- `POST /v1/admin/client/rotate-secret` (X-Admin-Token required)
- `GET /v1/admin/audit/recent` (X-Admin-Token required)
- `GET /admin` (web UI for license management)

## Database Migration
After containers are up, run:
```bash
docker compose exec api alembic upgrade head
```

See:
- `docs/architecture.md`
- `docs/api.md`
- `docs/vps-runbook.md`

## Reverse Proxy
Run API container on localhost (`127.0.0.1:8080`) and expose it through Apache or Nginx on your API subdomain.
