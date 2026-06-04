# ── Stage 1: build React frontend ─────────────────────────────────────────────
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt pyproject.toml README.md LICENSE ./
RUN pip install --no-cache-dir -r requirements.txt flower==2.0.1

# Copy source, then install the package itself to register the entry point
COPY flowforge/ flowforge/
COPY wsgi.py .
RUN pip install --no-cache-dir --no-deps .

COPY --from=frontend /build/dist/ frontend/dist/

RUN mkdir -p output

EXPOSE 5000
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-4} --worker-class gevent --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - wsgi:app"]
