# Production Dockerfile for LeadOps Core API Gateway
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install runtime system packages and SSL certs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install build dependencies, build wheels, and clean up
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# React SPA Frontend Builder
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Final runtime image
FROM base AS runner

COPY --from=builder /install /usr/local
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Create non-root user
RUN groupadd -g 10001 leadops && \
    useradd -u 10000 -g leadops -s /bin/bash -m leadops

# Copy application codebase
COPY agents /app/agents
COPY scripts /app/scripts
COPY run_server.py /app/run_server.py
COPY pytest.ini /app/pytest.ini

RUN mkdir -p /app/build_artifacts /app/backups && \
    chown -R leadops:leadops /app

USER leadops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "agents.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
