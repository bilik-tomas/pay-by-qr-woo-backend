# VPS Runbook

This runbook assumes:
- Debian 12 VPS
- Docker + Compose already installed
- subdomain prepared, e.g. `api.example.com`
- existing nginx on host

## 1. Clone and prepare branch
```bash
cd /home/tomas/projects
git clone <REPO_URL> pay-by-qr-woo-backend
cd /home/tomas/projects/pay-by-qr-woo-backend
git checkout dev/backend-bootstrap
cp .env.example .env
```

## 2. Configure `.env`
Set strong values:
```dotenv
APP_ENV=prod
APP_DEBUG=false
APP_LOG_LEVEL=INFO
API_PORT=8080
API_SIGN_TTL_SECONDS=300
ADMIN_TOKEN=<LONG_RANDOM_ADMIN_TOKEN>
API_CLIENTS=woo_prod:<LONG_RANDOM_SECRET>
DB_DSN=postgresql+psycopg://pbs:<STRONG_DB_PASS>@db:5432/pbs
REDIS_URL=redis://redis:6379/0
```

Important:
- keep `API_CLIENTS` secret outside plugin repo history
- use a different secret per environment (dev/stage/prod)

## 3. Start containers
```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

Run DB migrations:
```bash
docker compose exec api alembic upgrade head
```

Health check:
```bash
curl -s http://127.0.0.1:8080/health
```

## 4. Apache reverse proxy (api.subdomain.domain.tld)
If your VPS runs Apache, proxy the subdomain to internal API port `127.0.0.1:8080`.
If you change `API_PORT`, use that same port in `ProxyPass`.

Enable modules:
```bash
sudo a2enmod proxy proxy_http headers ssl rewrite
sudo systemctl restart apache2
```

Create `/etc/apache2/sites-available/pay-by-qr-api.conf`:
```apache
<VirtualHost *:80>
    ServerName api.subdomain.domain.tld
    RewriteEngine On
    RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>

<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName api.subdomain.domain.tld

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.subdomain.domain.tld/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.subdomain.domain.tld/privkey.pem

    ProxyPreserveHost On
    ProxyRequests Off
    RequestHeader set X-Forwarded-Proto "https"
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    LimitRequestBody 65536

    ErrorLog ${APACHE_LOG_DIR}/pay-by-qr-api-error.log
    CustomLog ${APACHE_LOG_DIR}/pay-by-qr-api-access.log combined
</VirtualHost>
</IfModule>
```

Enable site:
```bash
sudo a2ensite pay-by-qr-api.conf
sudo apachectl configtest
sudo systemctl reload apache2
```

## 5. TLS (Let's Encrypt)
Issue cert after DNS for `api.subdomain.domain.tld` points to VPS:
```bash
sudo certbot --apache -d api.subdomain.domain.tld
```

## 6. Firewall
Allow only:
- `22/tcp` SSH
- `80/tcp` and `443/tcp` nginx

Do not expose container ports publicly except localhost bind already configured.

## 7. Day-2 operations
Update deployment:
```bash
cd /home/tomas/projects/pay-by-qr-woo-backend
git pull
docker compose up -d --build
```

Backup volumes:
- PostgreSQL volume `pg_data`
- Redis volume `redis_data` (optional, can be rebuilt for nonce cache)

## 8. Plugin integration checklist
In WP plugin settings:
- API endpoint: `https://api.subdomain.domain.tld`
- client id: `woo_prod`
- client secret: `<LONG_RANDOM_SECRET>`
- license key: `<your license key>`

Then test one signed request from plugin to:
- `/v1/license/validate`
- `/v1/pbs/generate`

Optional admin seed via API:
```bash
curl -X POST https://api.example.com/v1/admin/license/upsert \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: <LONG_RANDOM_ADMIN_TOKEN>" \
  -d '{"license_key":"lic_demo_123456","status":"active","domain":"shop.example.com","plugin_instance_id":"","note":"seed"}'
```
