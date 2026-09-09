from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Configure engine with connection pooling and dialect-specific parameters
engine_kwargs = {"echo": settings.DB_ECHO}

if "sqlite" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initializes tables for development/testing and ensures schema compatibility."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Non-destructive column migrations for existing SQLite / Postgres tables
        scan_columns_to_add = [
            ("batch_number", "VARCHAR(100)"),
            ("batch_number_extracted", "VARCHAR(100)"),
            ("batch_number_confidence", "FLOAT DEFAULT 0.0"),
            ("batch_number_source", "VARCHAR(50) DEFAULT 'manual'"),
            ("batch_status", "VARCHAR(50) DEFAULT 'normal'"),
        ]
        
        for col_name, col_type in scan_columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE scans ADD COLUMN {col_name} {col_type}"))
            except Exception:
                # Column already exists
                pass

        declaration_columns_to_add = [
            ("raw_extracted_value", "TEXT"),
            ("normalized_numeric_value", "FLOAT"),
            ("normalized_unit", "VARCHAR(50)"),
            ("has_conflict", "BOOLEAN DEFAULT 0"),
            ("conflict_details", "TEXT"),
            ("original_ai_status", "VARCHAR(50)"),
            ("original_ai_confidence", "FLOAT DEFAULT 0.0"),
            ("violation_detection_rate", "FLOAT"),
            ("auto_confirm_threshold", "FLOAT DEFAULT 80.0"),
            ("workflow_decision", "VARCHAR(50)"),
            ("decision_method", "VARCHAR(50)"),
            ("decision_reason", "TEXT"),
            ("verification_status", "VARCHAR(50)"),
            ("verification_source", "VARCHAR(50)"),
            ("human_decision", "VARCHAR(50)"),
            ("reviewed_by", "VARCHAR(255)"),
            ("reviewed_at", "DATETIME"),
        ]

        for col_name, col_type in declaration_columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE declarations ADD COLUMN {col_name} {col_type}"))
            except Exception:
                # Column already exists
                pass

        scan_image_columns_to_add = [
            ("image_quality", "VARCHAR(50) DEFAULT 'CLEAR'"),
            ("sharpness_score", "FLOAT"),
            ("quality_threshold", "FLOAT DEFAULT 100.0"),
            ("quality_validated_at", "DATETIME"),
            ("analysis_allowed", "BOOLEAN DEFAULT 1"),
            ("quality_details_json", "JSON"),
        ]

        for col_name, col_type in scan_image_columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE scan_images ADD COLUMN {col_name} {col_type}"))
            except Exception:
                # Column already exists
                pass

        # Backfill existing declaration records for consistent persistence
        try:
            # 1. Update violation_detection_rate and auto_confirm_threshold where missing
            await conn.execute(text(
                "UPDATE declarations SET violation_detection_rate = ROUND(confidence_score * 100.0, 1) "
                "WHERE violation_detection_rate IS NULL AND confidence_score IS NOT NULL"
            ))
            await conn.execute(text(
                "UPDATE declarations SET auto_confirm_threshold = 80.0 WHERE auto_confirm_threshold IS NULL"
            ))

            # 2. Backfill declarations without human decisions: evaluate against threshold
            await conn.execute(text(
                "UPDATE declarations SET "
                "workflow_decision = 'AUTO_CONFIRMED', "
                "decision_method = 'SYSTEM_THRESHOLD', "
                "verification_status = 'AUTO_CONFIRMED', "
                "verification_source = 'SYSTEM_THRESHOLD' "
                "WHERE human_decision IS NULL "
                "AND (workflow_decision IS NULL OR workflow_decision = 'COMPLIANT' OR workflow_decision = 'AUTOMATICALLY_CONFIRMED') "
                "AND (violation_detection_rate >= auto_confirm_threshold OR (confidence_score * 100.0) >= auto_confirm_threshold) "
                "AND (severity IS NULL OR severity != 'needs_review')"
            ))

            await conn.execute(text(
                "UPDATE declarations SET "
                "workflow_decision = 'MANUAL_REVIEW_REQUIRED', "
                "decision_method = 'MANUAL', "
                "verification_status = 'MANUAL_REVIEW_REQUIRED', "
                "verification_source = 'MANUAL' "
                "WHERE human_decision IS NULL "
                "AND (workflow_decision IS NULL OR workflow_decision = 'COMPLIANT' OR workflow_decision = 'AUTOMATICALLY_CONFIRMED') "
                "AND ((violation_detection_rate < auto_confirm_threshold OR (confidence_score * 100.0) < auto_confirm_threshold) "
                "OR severity = 'needs_review')"
            ))

            # 3. Synchronize verification_status and verification_source for auto-confirmed items
            await conn.execute(text(
                "UPDATE declarations SET "
                "verification_status = 'AUTO_CONFIRMED', "
                "verification_source = 'SYSTEM_THRESHOLD' "
                "WHERE workflow_decision = 'AUTO_CONFIRMED' AND (human_decision IS NULL OR human_decision = 'NONE') "
                "AND (verification_status IS NULL OR verification_source IS NULL)"
            ))

            # 4. Synchronize verification_status for human-decided items
            await conn.execute(text(
                "UPDATE declarations SET "
                "verification_status = 'INSPECTOR_' || UPPER(human_decision), "
                "verification_source = 'INSPECTOR', "
                "workflow_decision = 'FINALIZED', "
                "decision_method = 'MANUAL' "
                "WHERE human_decision IS NOT NULL AND human_decision NOT IN ('NONE', 'AUTO-ANALYZED') "
                "AND (verification_status IS NULL OR verification_source IS NULL)"
            ))
        except Exception:
            pass

        # Deactivate obsolete reviewer/viewer roles to preserve historical integrity while denying authentication
        try:
            await conn.execute(text(
                "UPDATE users SET is_active = 0 WHERE lower(role) IN ('reviewer', 'viewer') "
                "OR email IN ('reviewer.patel@packcheck.gov.in', 'viewer@packcheck.gov.in')"
            ))
        except Exception:
            pass

async def seed_demo_users() -> None:
    """Create the login-page demo accounts when a fresh database is started."""
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        existing_user = (await session.execute(select(User.id).limit(1))).scalar_one_or_none()
        if existing_user:
            return

        session.add_all([
            User(
                name="Rajesh Kumar Verma",
                email="admin@packcheck.gov.in",
                phone="+919876543210",
                password_hash=hash_password("admin123"),
                role="admin",
                department="Central Legal Metrology Division",
                region="National HQ",
                is_active=True,
            ),
            User(
                name="Inspector Vikram Sharma",
                email="inspector.sharma@packcheck.gov.in",
                phone="+919876543212",
                password_hash=hash_password("inspector123"),
                role="inspector",
                department="Field Inspection Squad - Delhi North",
                region="Delhi NCR",
                is_active=True,
            ),
        ])
        await session.commit()
