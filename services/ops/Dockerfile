FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY services/common /app/services/common

# Copy service code
COPY services/ops /app/services/ops

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi[all] \
    uvicorn \
    sqlalchemy[asyncio] \
    asyncpg \
    pydantic-settings \
    python-jose[cryptography] \
    httpx \
    minio \
    nats-py \
    redis \
    apscheduler \
    cryptography \
    prometheus_client \
    alembic

WORKDIR /app/services/ops

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
