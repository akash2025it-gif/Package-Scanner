from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession


class AuditService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Persists an immutable audit log record."""
        # Lazy import to avoid circular dependency
        from app.models.audit import AuditLog
        
        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            timestamp=datetime.now(timezone.utc),
            metadata_json=metadata or {},
        )
        db.add(audit_entry)
        await db.flush()
        return audit_entry
