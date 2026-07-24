# ── Stage 1: build React frontend ─────────────────────────────────────────────
FROM node:26-alpine@sha256:e88a35be04478413b7c71c455cd9865de9b9360e1f43456be5951032d7ac1a66 AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
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
