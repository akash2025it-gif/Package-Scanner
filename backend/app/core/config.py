import os
import shutil
import tempfile
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_FILE = os.path.join(BACKEND_DIR, "packcheck.db")
DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE.replace(chr(92), '/')}"

if os.environ.get("VERCEL"):
    system_tmp = tempfile.gettempdir()
    tmp_db = os.path.join(system_tmp, "packcheck.db")
    if not os.path.exists(tmp_db):
        candidates = [
            DEFAULT_DB_FILE,
            os.path.join(os.getcwd(), "backend", "packcheck.db"),
            os.path.join(os.getcwd(), "packcheck.db"),
            "/var/task/backend/packcheck.db",
            "/var/task/packcheck.db",
        ]
        for cand in candidates:
            if os.path.exists(cand):
                try:
                    shutil.copyfile(cand, tmp_db)
                    break
                except Exception:
                    pass
    DEFAULT_SQLITE_URL = f"sqlite+aiosqlite:///{tmp_db.replace(chr(92), '/')}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    APP_NAME: str = "PackCheck API"
    APP_ENV: str = "production" if os.environ.get("VERCEL") else "development"
    DEBUG: bool = False if os.environ.get("VERCEL") else True
    API_V1_PREFIX: str = "/api/v1"
    
    # Secret key for JWT signing
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "packcheck-super-secret-production-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default Seed Passwords (configurable via environment)
    DEFAULT_ADMIN_PASSWORD: str = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
    DEFAULT_INSPECTOR_PASSWORD: str = os.environ.get("DEFAULT_INSPECTOR_PASSWORD", "inspector123")

    # Database
    DATABASE_URL: str = DEFAULT_SQLITE_URL
    DB_ECHO: bool = False

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = (
        "https://package-scanner-rust.vercel.app,"
        "https://package-scanner-8ayk.vercel.app,"
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:5173"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        return self.CORS_ORIGINS

    # Storage
    STORAGE_PROVIDER: str = "local"  # "local", "s3", "minio"
    LOCAL_STORAGE_DIR: str = os.path.join(tempfile.gettempdir(), "uploads") if os.environ.get("VERCEL") else os.path.join(BACKEND_DIR, "uploads")
    REPORTS_DIR: str = os.path.join(tempfile.gettempdir(), "reports") if os.environ.get("VERCEL") else os.path.join(BACKEND_DIR, "reports")

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
    OCR_PROVIDER: str = "real"  # "real", "google_vision", "tesseract", "windows_media"
    OCR_SPACE_API_KEY: str = os.environ.get("OCR_SPACE_API_KEY", "helloworld")
    GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    REGION_DETECTOR_PROVIDER: str = "heuristic"  # "heuristic", "yolo_service"
    YOLO_SERVICE_URL: str = "http://localhost:8501/v1/models/lmpc-detector:predict"

    # Rate Limiting
    ANALYZE_RATE_LIMIT_PER_MINUTE: int = 20

    # Compliance Automation Threshold (Mandatory Declarations Audit)
    AUTO_CONFIRM_VIOLATION_THRESHOLD: float = 80.0

    # Image Quality / Blur Validation Gate Settings
    BLUR_THRESHOLD: float = 60.0  # Calibrated Laplacian variance threshold (separates blurry from clear images)
    MIN_IMAGE_DIMENSION: int = 100  # Minimum width/height in px for reliable OCR extraction


settings = Settings()

# Ensure local directories exist if local storage is used
try:
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
except Exception:
    pass
