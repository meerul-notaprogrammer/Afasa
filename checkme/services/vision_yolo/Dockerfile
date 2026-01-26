FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Minimal system deps (headless) - NO mesa/X11
# Added retries for robustness
RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy common library
COPY services/common /app/services/common

# Copy service code
COPY services/vision_yolo /app/services/vision_yolo

# Install dependencies
# Explicitly using opencv-python-headless and ensuring numpy compatibility
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    "opencv-python-headless>=4.10.0.84" \
    "numpy<2" \
    "ultralytics==8.3.0" \
    "fastapi[all]" \
    "uvicorn" \
    "sqlalchemy[asyncio]" \
    "asyncpg" \
    "pydantic-settings" \
    "python-jose[cryptography]" \
    "httpx" \
    "minio" \
    "nats-py" \
    "redis" \
    "Pillow" \
    "cryptography" \
    "prometheus_client"

WORKDIR /app/services/vision_yolo

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
