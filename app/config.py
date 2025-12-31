"""Application Configuration Management"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "AEC Collaboration Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str
    
    # Storage Backend
    storage_backend: str = "minio"  # "minio" or "oss"
    
    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "aec-platform"
    minio_secure: bool = False
    
    # OSS
    oss_endpoint: Optional[str] = None
    oss_access_key: Optional[str] = None
    oss_secret_key: Optional[str] = None
    oss_bucket: Optional[str] = None
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str


# Global settings instance
settings = Settings()
