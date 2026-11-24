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
    APP_ENV: str = os.environ.get("APP_ENV", "development")
    DEBUG: bool = False if (os.environ.get("VERCEL") or os.environ.get("APP_ENV") == "production") else True
    API_V1_PREFIX: str = "/api/v1"
    
    # Secret key for JWT signing
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Initial Seed Credentials (configurable via environment, safe fallback for serverless preview demo)
    INITIAL_ADMIN_EMAIL: str = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@packcheck.gov.in")
    INITIAL_ADMIN_PASSWORD: Optional[str] = (
        os.environ.get("INITIAL_ADMIN_PASSWORD") or os.environ.get("DEFAULT_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
    )
    INITIAL_INSPECTOR_EMAIL: str = os.environ.get("INITIAL_INSPECTOR_EMAIL", "inspector.sharma@packcheck.gov.in")
    INITIAL_INSPECTOR_PASSWORD: Optional[str] = (
        os.environ.get("INITIAL_INSPECTOR_PASSWORD") or os.environ.get("DEFAULT_INSPECTOR_PASSWORD") or os.environ.get("INSPECTOR_PASSWORD")
    )

    # Aliases for backwards compatibility in existing codebase
    @property
    def DEFAULT_ADMIN_PASSWORD(self) -> Optional[str]:
        return self.INITIAL_ADMIN_PASSWORD

    @property
    def DEFAULT_INSPECTOR_PASSWORD(self) -> Optional[str]:
        return self.INITIAL_INSPECTOR_PASSWORD

    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    DB_ECHO: bool = False

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> str:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_strict_prod = (app_env == "production")
        val = (v or "").strip()
        
        insecure_keys = {
            "packcheck-super-secret-production-key-change-me",
            "packcheck-dev-secret-key-super-secure-token-2026",
            "secret",
            "changeme",
            "default",
            "admin",
            "packcheck-dev-environment-secure-signing-key-32chars-min",
        }
        
        if is_strict_prod:
            if not val:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: SECRET_KEY environment variable is missing. "
                    "Production deployments require an explicitly configured, cryptographically strong SECRET_KEY "
                    "of at least 32 characters/bytes (e.g., generated with 'openssl rand -hex 32'). "
                    "Deterministic derivation and fallback keys are strictly prohibited in production."
                )
            if len(val) < 32 or val in insecure_keys:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION: A cryptographically strong SECRET_KEY "
                    "(minimum 32 characters/bytes) must be supplied in production. "
                    "Insecure, default, and short keys are rejected."
                )
            return val
            
        if val:
            if len(val) >= 32 and val not in insecure_keys:
                return val

        # Serverless preview / development resilient fallback
        if os.environ.get("VERCEL"):
            import hashlib
            seed = os.environ.get("VERCEL_DEPLOYMENT_ID") or os.environ.get("VERCEL_URL") or "packcheck-serverless-resilient-seed"
            return hashlib.sha256(f"packcheck-jwt-signing-key:{seed}".encode()).hexdigest()

        return "packcheck-dev-environment-secure-signing-key-32chars-min"

    @field_validator("INITIAL_ADMIN_PASSWORD", mode="before")
    @classmethod
    def validate_admin_password(cls, v: Optional[str]) -> Optional[str]:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_strict_prod = (app_env == "production")
        val = (v or "").strip()
        if is_strict_prod:
            return val if val else None
        return val if val else "admin123"

    @field_validator("INITIAL_INSPECTOR_PASSWORD", mode="before")
    @classmethod
    def validate_inspector_password(cls, v: Optional[str]) -> Optional[str]:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_strict_prod = (app_env == "production")
        val = (v or "").strip()
        if is_strict_prod:
            return val if val else None
        return val if val else "inspector123"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        app_env = (os.environ.get("APP_ENV") or "").lower().strip()
        is_strict_prod = (app_env == "production")
        url = (v or "").strip()
        
        if is_strict_prod:
            if not url:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: DATABASE_URL environment variable is missing. "
                    "Production deployments (including Vercel) require a persistent PostgreSQL database connection string "
                    "(e.g., 'postgresql+asyncpg://user:password@host:5432/dbname' or 'postgresql://...'). "
                    "Silent fallback to ephemeral SQLite is strictly prohibited in production."
                )
            if url.startswith("sqlite") or "sqlite" in url:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: Ephemeral SQLite is strictly prohibited in production. "
                    "A persistent external PostgreSQL connection is required via DATABASE_URL."
                )
        else:
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
        # Normalize SQLite for aiosqlite (development only)
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
