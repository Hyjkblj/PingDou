from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PINGDOU_",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = (
        "mysql+pymysql://pingdou:pingdou_dev@127.0.0.1:3306/"
        "pingdou?charset=utf8mb4"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-secret-change-me-at-least-32-bytes"
    storage_dir: Path = Path("./storage")
    public_base_url: str = "http://localhost:8000"
    job_eager: bool = True
    fake_sms_code: str = "123456"
    access_token_ttl_seconds: int = 7200
    refresh_token_ttl_seconds: int = 2_592_000
    max_upload_bytes: int = 20 * 1024 * 1024

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "pingdou"
    minio_secure: bool = False

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
