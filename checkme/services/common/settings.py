"""
AFASA 2.0 - Shared Settings
Centralized configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://afasa:afasa_pass@postgres:5432/afasa"
    
    # NATS
    nats_url: str = "nats://nats:4222"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio_pass"
    minio_bucket: str = "afasa"
    minio_secure: bool = False
    
    # OIDC / Keycloak
    oidc_issuer_url: str = "http://keycloak:8080/realms/afasa"
    oidc_audience: str = "afasa-api"
    
    # Secrets encryption
    afasa_master_key_base64: str = ""
    
    # ThingsBoard
    tb_base_url: str = ""
    tb_jwt: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    public_base_url: str = ""
    
    # Gemini
    gemini_api_key: str = ""
    
    # MediaMTX
    mediamtx_api_base: str = "http://mediamtx:8888"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
