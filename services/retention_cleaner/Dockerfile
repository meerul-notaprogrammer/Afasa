FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY services/common /app/services/common

# Copy service code
COPY services/retention_cleaner /app/services/retention_cleaner

# Install dependencies
RUN pip install --no-cache-dir \
    sqlalchemy[asyncio] \
    asyncpg \
    pydantic-settings \
    minio \
    apscheduler \
    structlog \
    prometheus_client \
    httpx \
    redis \
    python-jose \
    cryptography

WORKDIR /app/services/retention_cleaner

CMD ["python", "-m", "app.main"]
