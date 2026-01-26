FROM python:3.11-slim

WORKDIR /app

# Copy common library
COPY services/common /app/services/common

# Copy service code
COPY services/tb_adapter /app/services/tb_adapter

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
    cryptography \
    prometheus_client \
    redis

WORKDIR /app/services/tb_adapter

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
