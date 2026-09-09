from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    APP_NAME: str = "PackCheck API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Secret key for JWT signing
    SECRET_KEY: str = "packcheck-super-secret-production-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for convenience in testing
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/packcheck.db" if os.environ.get("VERCEL") else "sqlite+aiosqlite:///./packcheck.db"
    DB_ECHO: bool = False

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        return self.CORS_ORIGINS

    # Storage
    STORAGE_PROVIDER: str = "local"  # "local", "s3", "minio"
    LOCAL_STORAGE_DIR: str = "/tmp/uploads" if os.environ.get("VERCEL") else "./uploads"
    REPORTS_DIR: str = "/tmp/reports" if os.environ.get("VERCEL") else "./reports"

    # S3 / MinIO
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: Optional[str] = "minioadmin"
    S3_SECRET_KEY: Optional[str] = "minioadmin"
    S3_BUCKET_NAME: str = "packcheck-labels"
    S3_REGION: str = "us-east-1"

    # Celery & Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = True

    # AI / Vision / OCR Providers
    OCR_PROVIDER: str = "mock"  # "mock", "google_vision", "tesseract"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    REGION_DETECTOR_PROVIDER: str = "heuristic"  # "heuristic", "yolo_service"
    YOLO_SERVICE_URL: str = "http://localhost:8501/v1/models/lmpc-detector:predict"

    # Rate Limiting
    ANALYZE_RATE_LIMIT_PER_MINUTE: int = 20

    # Compliance Automation Threshold (Mandatory Declarations Audit)
    AUTO_CONFIRM_VIOLATION_THRESHOLD: float = 80.0

    # Image Quality / Blur Validation Gate Settings
    BLUR_THRESHOLD: float = 100.0  # Minimum Laplacian variance for an image to be considered CLEAR
    MIN_IMAGE_DIMENSION: int = 100  # Minimum width/height in px for reliable OCR extraction


settings = Settings()

# Ensure local directories exist if local storage is used
os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)
