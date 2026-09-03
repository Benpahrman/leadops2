# Copyright 2026 Google LLC
# Autonomous Agent Worker Dockerfile with Playwright & Headless Chromium

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8080

WORKDIR /code

# Install system utilities and uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.8.13 playwright

# Install Chromium dependencies for headless browsing agents
RUN playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./workers ./workers

RUN uv sync --frozen

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "workers.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
