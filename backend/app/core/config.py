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
    APP_ENV: str = "production" if os.environ.get("VERCEL") else os.environ.get("APP_ENV", "development")
    DEBUG: bool = False if (os.environ.get("VERCEL") or os.environ.get("APP_ENV") == "production") else True
    API_V1_PREFIX: str = "/api/v1"
    
    # Secret key for JWT signing
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Seed Passwords (configurable via environment, NO hardcoded production fallbacks)
    DEFAULT_ADMIN_PASSWORD: Optional[str] = os.environ.get("DEFAULT_ADMIN_PASSWORD") or os.environ.get("ADMIN_INITIAL_PASSWORD")
    DEFAULT_INSPECTOR_PASSWORD: Optional[str] = os.environ.get("DEFAULT_INSPECTOR_PASSWORD") or os.environ.get("INSPECTOR_INITIAL_PASSWORD")

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)
    DB_ECHO: bool = False

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> str:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_production = (app_env == "production") or bool(os.environ.get("VERCEL"))
        val = (v or "").strip()
        
        insecure_keys = {
            "packcheck-super-secret-production-key-change-me",
            "packcheck-dev-secret-key-super-secure-token-2026",
            "secret",
            "changeme",
            "default",
            "admin",
        }
        
        if is_production:
            if not val or val in insecure_keys or len(val) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION: A cryptographically strong SECRET_KEY "
                    "(minimum 32 characters) must be supplied via environment variables in production."
                )
            return val
            
        # Development / Testing fallback
        if not val or val in insecure_keys:
            return "packcheck-dev-environment-secure-signing-key-32chars-min"
        return val

    @field_validator("DEFAULT_ADMIN_PASSWORD", mode="before")
    @classmethod
    def validate_admin_password(cls, v: Optional[str]) -> Optional[str]:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_production = (app_env == "production") or bool(os.environ.get("VERCEL"))
        val = (v or "").strip()
        if is_production:
            # Never fallback to hardcoded default password in production
            return val if val else None
        return val if val else "admin123"

    @field_validator("DEFAULT_INSPECTOR_PASSWORD", mode="before")
    @classmethod
    def validate_inspector_password(cls, v: Optional[str]) -> Optional[str]:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_production = (app_env == "production") or bool(os.environ.get("VERCEL"))
        val = (v or "").strip()
        if is_production:
            # Never fallback to hardcoded default password in production
            return val if val else None
        return val if val else "inspector123"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        url = (v or "").strip()
        if not url:
            if os.environ.get("VERCEL"):
                system_tmp = tempfile.gettempdir()
                tmp_db = os.path.join(system_tmp, "packcheck.db")
                return f"sqlite+aiosqlite:///{tmp_db.replace(chr(92), '/')}"
            return DEFAULT_SQLITE_URL
        
        # Normalize Postgres dialects for SQLAlchemy asyncpg
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Normalize SQLite for aiosqlite
        elif url.startswith("sqlite://") and not url.startswith("sqlite+"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            
        return url

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
