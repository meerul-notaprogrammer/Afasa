"""
AFASA 2.0 - Audit Service
Append-only audit logging with AI reason/confidence support
"""
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import UUID, uuid4
import json

from sqlalchemy import select
from .db import get_tenant_session
from .models import AuditLog


class AuditService:
    """Append-only audit logging service"""
    
    @staticmethod
    async def log(
        tenant_id: str,
        actor_type: str,  # 'user', 'ai', 'system'
        action: str,
        target_type: str,
        target_id: str,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        confidence: Optional[float] = None,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        correlation_id: Optional[UUID] = None
    ) -> UUID:
        """
        Create an audit log entry.
        Audit log is append-only - no updates or deletes allowed.
        """
        async with get_tenant_session(tenant_id) as session:
            entry = AuditLog(
                id=uuid4(),
                tenant_id=UUID(tenant_id),
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                reason=reason,
                confidence=confidence,
                before=before,
                after=after,
                occurred_at=datetime.now(timezone.utc),
                correlation_id=correlation_id
            )
            session.add(entry)
            await session.flush()
            return entry.id
    
    @staticmethod
    async def query(
        tenant_id: str,
        actor_type: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list:
        """Query audit log entries"""
        async with get_tenant_session(tenant_id) as session:
            query = select(AuditLog).order_by(AuditLog.occurred_at.desc())
            
            if actor_type:
                query = query.where(AuditLog.actor_type == actor_type)
            if action:
                query = query.where(AuditLog.action == action)
            if target_type:
                query = query.where(AuditLog.target_type == target_type)
            if from_date:
                query = query.where(AuditLog.occurred_at >= from_date)
            if to_date:
                query = query.where(AuditLog.occurred_at <= to_date)
            
            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            return list(result.scalars().all())


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
