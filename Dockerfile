# ── Stage 1: build React frontend ─────────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY flowforge/ flowforge/
COPY --from=frontend /build/dist/ frontend/dist/

RUN mkdir -p output

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]
