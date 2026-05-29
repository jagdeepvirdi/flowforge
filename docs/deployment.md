# FlowForge — Production Deployment Guide

Covers two deployment paths:

- **[Option A — Docker Compose](#option-a--docker-compose)** — recommended for most self-hosters; one command to run everything
- **[Option B — Bare Metal (Gunicorn + Nginx)](#option-b--bare-metal-gunicorn--nginx)** — for servers where Docker is not available or not wanted

Both paths end with the same [post-deployment checklist](#post-deployment-checklist).

---

## Prerequisites

| Component | Requirement |
|---|---|
| OS | Ubuntu 22.04 / Debian 12 or any Linux — macOS works for testing |
| PostgreSQL | 14+ (managed service like RDS works too) |
| Python | 3.11+ (bare-metal only) |
| Node.js | 20+ (bare-metal only — to build the frontend) |
| Docker + Docker Compose | v2.24+ (Docker path only) |

---

## Option A — Docker Compose

The repository ships with a `Dockerfile` (multi-stage: React build + Python runtime) and `docker-compose.yml` that starts three containers: `db` (PostgreSQL), `app` (Gunicorn), and `scheduler` (APScheduler daemon).

### 1. Clone and configure

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge
cp .env.example .env
```

Edit `.env` — minimum required values:

```env
FLOWFORGE_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
FLOWFORGE_JWT_SECRET=<run: python -c "import secrets; print(secrets.token_hex(32))">
FLOWFORGE_USERNAME=admin
FLOWFORGE_PASSWORD=<bcrypt hash — see below>
```

Generate the bcrypt password hash:

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

The `docker-compose.yml` sets `FLOWFORGE_DB_URL` internally to the bundled `db` container. Override it if you want to point to an external PostgreSQL:

```env
FLOWFORGE_DB_URL=postgresql://user:pass@your-rds-host:5432/flowforge
```

### 2. Build and start

```bash
docker compose up -d --build
```

This:
1. Builds the React frontend inside a Node 20 stage
2. Builds the Python runtime layer and installs Gunicorn
3. Starts PostgreSQL, then the API (health-checked), then the scheduler

Check logs:

```bash
docker compose logs -f app
docker compose logs -f scheduler
```

### 3. Oracle data sources (optional)

If your pipelines connect to Oracle databases, use the Oracle overlay file:

```bash
docker compose -f docker-compose.yml -f docker-compose.oracle.yml up -d --build
```

The overlay adds `python-oracledb` to the image. No Oracle Instant Client is needed — `python-oracledb` runs in thin mode (pure Python).

### 4. Apply migrations and create admin user

On first start, run migrations inside the running container:

```bash
docker compose exec app flowforge db upgrade
```

The admin user is seeded automatically from `FLOWFORGE_USERNAME` / `FLOWFORGE_PASSWORD` on first `db upgrade`. Re-running is safe — it skips if a user already exists.

### 5. Access the UI

`http://your-server-ip:5000`

To put Nginx in front (port 80/443), see [Nginx reverse proxy config](#nginx-reverse-proxy-config) below — it applies to both Docker and bare-metal.

---

## Option B — Bare Metal (Gunicorn + Nginx)

### 1. System setup

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx
```

### 2. Create a system user

Running as a dedicated user limits blast radius if the app is compromised:

```bash
sudo useradd --system --home /opt/flowforge --shell /usr/sbin/nologin flowforge
sudo mkdir -p /opt/flowforge
sudo chown flowforge:flowforge /opt/flowforge
```

### 3. Clone and install

```bash
sudo -u flowforge git clone https://github.com/jagdeepvirdi/flowforge.git /opt/flowforge/app
cd /opt/flowforge/app

sudo -u flowforge python3.11 -m venv .venv
sudo -u flowforge .venv/bin/pip install -e ".[all]"   # core + Gmail + Drive + M365 + PDF
sudo -u flowforge .venv/bin/pip install gunicorn
```

### 4. Build the frontend

```bash
cd /opt/flowforge/app/frontend
sudo -u flowforge npm ci --silent
sudo -u flowforge npm run build
# Output: frontend/dist/ — Flask serves this as static files
```

### 5. Configure the environment

```bash
sudo -u flowforge cp /opt/flowforge/app/.env.example /opt/flowforge/app/.env
sudo chmod 640 /opt/flowforge/app/.env
```

Edit `/opt/flowforge/app/.env`:

```env
FLOWFORGE_DB_URL=postgresql://flowforge:strongpassword@localhost:5432/flowforge
FLOWFORGE_SECRET_KEY=<generate>
FLOWFORGE_JWT_SECRET=<generate — different value from SECRET_KEY>
FLOWFORGE_USERNAME=admin
FLOWFORGE_PASSWORD=<bcrypt hash>
FLOWFORGE_TRUSTED_PROXIES=1   # tells the app it's behind Nginx
FLOWFORGE_CORS_ORIGIN=https://your-domain.com
FLOWFORGE_PORT=5000
```

> Set `FLOWFORGE_TRUSTED_PROXIES=1` whenever Nginx (or any reverse proxy) sits in front. This lets Flask see the real client IP for rate limiting instead of `127.0.0.1`.

### 6. Apply migrations

```bash
sudo -u flowforge /opt/flowforge/app/.venv/bin/flowforge db upgrade
```

This creates all tables and seeds the admin user.

### 7. Create the output directory

```bash
sudo mkdir -p /opt/flowforge/output
sudo chown flowforge:flowforge /opt/flowforge/output
```

Reports are written here. Point `FLOWFORGE_OUTPUT_DIR` to this path if you want them outside the repo directory.

### 8. Systemd service — Gunicorn API

Create `/etc/systemd/system/flowforge-api.service`:

```ini
[Unit]
Description=FlowForge API (Gunicorn)
After=network.target postgresql.service

[Service]
Type=simple
User=flowforge
WorkingDirectory=/opt/flowforge/app
EnvironmentFile=/opt/flowforge/app/.env
ExecStart=/opt/flowforge/app/.venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    "flowforge.api.app:create_app()"
Restart=on-failure
RestartSec=5
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
```

**Worker count rule of thumb**: `(2 × CPU cores) + 1`. On a 2-core VM: 5 workers. Keep `--timeout 120` — pipeline steps that generate reports or send email can take tens of seconds.

### 9. Systemd service — APScheduler

Create `/etc/systemd/system/flowforge-scheduler.service`:

```ini
[Unit]
Description=FlowForge Scheduler
After=network.target flowforge-api.service

[Service]
Type=simple
User=flowforge
WorkingDirectory=/opt/flowforge/app
EnvironmentFile=/opt/flowforge/app/.env
ExecStart=/opt/flowforge/app/.venv/bin/flowforge schedule
Restart=on-failure
RestartSec=10
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
```

### 10. Systemd service — Celery worker (optional)

Only needed if `FLOWFORGE_REDIS_URL` is set for async pipeline execution. Create `/etc/systemd/system/flowforge-worker.service`:

```ini
[Unit]
Description=FlowForge Celery Worker
After=network.target flowforge-api.service

[Service]
Type=simple
User=flowforge
WorkingDirectory=/opt/flowforge/app
EnvironmentFile=/opt/flowforge/app/.env
ExecStart=/opt/flowforge/app/.venv/bin/flowforge worker --concurrency 2
Restart=on-failure
RestartSec=10
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
```

Enable and start all services:

```bash
sudo systemctl daemon-reload
# Core (always):
sudo systemctl enable --now flowforge-api flowforge-scheduler
# Optional (only if using Redis/Celery):
sudo systemctl enable --now flowforge-worker
sudo systemctl status flowforge-api flowforge-scheduler
```

Tail logs:

```bash
sudo journalctl -u flowforge-api -f
sudo journalctl -u flowforge-scheduler -f
sudo journalctl -u flowforge-worker -f   # if using Celery
```

---

## Nginx Reverse Proxy Config

Applies to both Docker and bare-metal. Create `/etc/nginx/sites-available/flowforge`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Increase max upload size if you use large Excel templates or bulk-load files
    client_max_body_size 50M;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # match gunicorn --timeout
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/flowforge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### TLS with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com
```

Certbot edits the Nginx config automatically and installs a cron for auto-renewal.

---

## Post-Deployment Checklist

Run these after either deployment path:

- [ ] `curl https://your-domain.com/api/health` → `{"status": "ok"}`
- [ ] Log in to the UI — dashboard loads, sidebar nav works
- [ ] Go to **Connections** → add a DB connection → **Test** button returns success
- [ ] Create a minimal test pipeline (no steps) → **Run Now** → status shows Success in Run History
- [ ] Verify the scheduler is registered: check **Run History** for a scheduled pipeline after its next cron fire time
- [ ] If using Gmail / M365: send a test email from the Email Designer
- [ ] Confirm `.env` is not world-readable: `ls -la /opt/flowforge/app/.env` → `-rw-r-----`

---

## Upgrades

```bash
# 1. Pull the new version
cd /opt/flowforge/app
sudo -u flowforge git pull

# 2. Install any new Python dependencies
sudo -u flowforge .venv/bin/pip install -e ".[all]"

# 3. Rebuild the frontend (only if frontend/ changed)
cd frontend && sudo -u flowforge npm ci --silent && sudo -u flowforge npm run build && cd ..

# 4. Apply database migrations
sudo -u flowforge .venv/bin/flowforge db upgrade

# 5. Restart services
sudo systemctl restart flowforge-api flowforge-scheduler
```

For Docker:

```bash
docker compose pull    # if using a registry
docker compose up -d --build
docker compose exec app flowforge db upgrade
```

---

## Environment Variable Reference

| Variable | Required | Notes |
|---|---|---|
| `FLOWFORGE_DB_URL` | Yes | PostgreSQL DSN for FlowForge's config database |
| `FLOWFORGE_SECRET_KEY` | Yes | AES-256 key for credential encryption — never change after first run |
| `FLOWFORGE_JWT_SECRET` | Yes (prod) | JWT signing secret — falls back to `SECRET_KEY` with a warning if unset |
| `FLOWFORGE_USERNAME` | Yes | Admin login username |
| `FLOWFORGE_PASSWORD` | Yes | Admin login password, bcrypt-hashed |
| `FLOWFORGE_PORT` | No | API port (default: `5000`) |
| `FLOWFORGE_TRUSTED_PROXIES` | Yes (behind proxy) | Set to `1` when behind Nginx/ALB — enables `X-Forwarded-For` unwrapping |
| `FLOWFORGE_CORS_ORIGIN` | Yes (prod) | Allowed CORS origin, e.g. `https://your-domain.com` |
| `FLOWFORGE_ATTACHMENT_MAX_MB` | No | Default attachment size threshold (default: `10`) |

See `.env.example` for the full list including Gmail, M365, Drive, and AI variables.

---

## Related

- [Getting Started](getting-started.md) — local dev setup, first pipeline, CLI reference
- [Running the Server](running-the-server.md) — dev mode, `flowforge.ps1` / `flowforge.sh`, prod mode scripts
- [RUNBOOK.md](RUNBOOK.md) — Alembic migration workflow, DB stamp scenario, scheduler diagnostics
