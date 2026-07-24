# ── Stage 1: build React frontend ─────────────────────────────────────────────
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6
WORKDIR /app

# Non-root user the process actually runs as (see USER below) — created early so
# later COPY/mkdir layers can chown straight to it without a second RUN layer.
RUN groupadd --system --gid 1000 flowforge \
 && useradd --system --uid 1000 --gid flowforge --home-dir /app --shell /usr/sbin/nologin flowforge

# Install dependencies first (cached layer)
COPY requirements.txt pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy source, then install the package itself to register the entry point
COPY flowforge/ flowforge/
COPY wsgi.py .
RUN pip install --no-cache-dir --no-deps .

COPY --from=frontend /build/dist/ frontend/dist/

# output/ and logs/ are where the running app actually writes (reports, audit log);
# everything else under /app only needs to be readable by the runtime user.
RUN mkdir -p output logs && chown -R flowforge:flowforge /app

USER flowforge

EXPOSE 5000
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-4} --worker-class gevent --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - wsgi:app"]
