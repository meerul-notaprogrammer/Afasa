FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg for snapshot capture
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy common library
COPY services/common /app/services/common

# Copy service code
COPY services/media /app/services/media

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
    Pillow \
    onvif-zeep \
    cryptography \
    prometheus_client \
    alembic

WORKDIR /app/services/media

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
