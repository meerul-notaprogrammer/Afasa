"""
AFASA 2.0 - Ops Service Extended Routes
Settings, Audit, and Me endpoints
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, require_role, TokenPayload, get_tenant_session,
    TenantSettings, Tenant, AuditLog, get_audit_service
)

router = APIRouter()


# ============================================================================
# /api/me - User Context
# ============================================================================

class MeResponse(BaseModel):
    tenant_id: str
    user_id: str
    email: Optional[str]
    roles: List[str]
    tenant_name: str
    settings_summary: dict


@router.get("/me", response_model=MeResponse, tags=["me"])
async def get_me(token: TokenPayload = Depends(verify_token)):
    """Get current user's context including tenant info"""
    async with get_tenant_session(token.tenant_id) as session:
        # Get tenant
        result = await session.execute(
            select(Tenant).where(Tenant.id == UUID(token.tenant_id))
        )
        tenant = result.scalar_one_or_none()
        
        # Get settings
        result = await session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == UUID(token.tenant_id))
        )
        settings = result.scalar_one_or_none()
        
        return MeResponse(
            tenant_id=token.tenant_id,
            user_id=token.sub,
            email=getattr(token, 'email', None),
            roles=token.roles,
            tenant_name=tenant.name if tenant else "Unknown",
            settings_summary={
                "ai_rule_creation": settings.ai_rule_creation if settings else "suggest_only",
                "retention_snapshots_days": settings.retention_snapshots_days if settings else 30,
            }
        )


# ============================================================================
# /api/settings - Tenant Settings
# ============================================================================

class AISettingsUpdate(BaseModel):
    ai_rule_creation: Optional[str] = None  # suggest_only | allow
    ai_auto_activation: Optional[bool] = None
    max_daily_rule_changes: Optional[int] = None


class RetentionSettingsUpdate(BaseModel):
    retention_snapshots_days: Optional[int] = None
    retention_annotated_days: Optional[int] = None
    retention_reports_days: Optional[int] = None


class AlertSettingsUpdate(BaseModel):
    alert_cooldown_minutes: Optional[int] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    max_daily_alerts: Optional[int] = None


class SettingsResponse(BaseModel):
    ai_rule_creation: str
    ai_auto_activation: bool
    max_daily_rule_changes: int
    protected_devices: list
    protected_rules: list
    retention_snapshots_days: int
    retention_annotated_days: int
    retention_reports_days: int
    
    class Config:
        from_attributes = True


@router.get("/settings", response_model=SettingsResponse, tags=["settings"])
async def get_settings(token: TokenPayload = Depends(verify_token)):
    """Get tenant settings"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == UUID(token.tenant_id))
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        
        return settings


@router.post("/settings/ai", tags=["settings"])
async def update_ai_settings(
    body: AISettingsUpdate,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Update AI governance settings"""
    audit = get_audit_service()
    
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == UUID(token.tenant_id))
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        
        before = {
            "ai_rule_creation": settings.ai_rule_creation,
            "ai_auto_activation": settings.ai_auto_activation,
            "max_daily_rule_changes": settings.max_daily_rule_changes
        }
        
        if body.ai_rule_creation is not None:
            settings.ai_rule_creation = body.ai_rule_creation
        if body.ai_auto_activation is not None:
            settings.ai_auto_activation = body.ai_auto_activation
        if body.max_daily_rule_changes is not None:
            settings.max_daily_rule_changes = body.max_daily_rule_changes
        
        settings.updated_at = datetime.now(timezone.utc)
        await session.flush()
        
        after = {
            "ai_rule_creation": settings.ai_rule_creation,
            "ai_auto_activation": settings.ai_auto_activation,
            "max_daily_rule_changes": settings.max_daily_rule_changes
        }
        
    # Audit log
    await audit.log(
        tenant_id=token.tenant_id,
        actor_type="user",
        actor_id=token.sub,
        action="settings.ai.updated",
        target_type="tenant_settings",
        target_id=token.tenant_id,
        before=before,
        after=after
    )
    
    return {"success": True}


@router.post("/settings/retention", tags=["settings"])
async def update_retention_settings(
    body: RetentionSettingsUpdate,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Update retention settings"""
    audit = get_audit_service()
    
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == UUID(token.tenant_id))
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        
        before = {
            "retention_snapshots_days": settings.retention_snapshots_days,
            "retention_annotated_days": settings.retention_annotated_days,
            "retention_reports_days": settings.retention_reports_days
        }
        
        if body.retention_snapshots_days is not None:
            settings.retention_snapshots_days = body.retention_snapshots_days
        if body.retention_annotated_days is not None:
            settings.retention_annotated_days = body.retention_annotated_days
        if body.retention_reports_days is not None:
            settings.retention_reports_days = body.retention_reports_days
        
        settings.updated_at = datetime.now(timezone.utc)
        await session.flush()
        
        after = {
            "retention_snapshots_days": settings.retention_snapshots_days,
            "retention_annotated_days": settings.retention_annotated_days,
            "retention_reports_days": settings.retention_reports_days
        }
    
    await audit.log(
        tenant_id=token.tenant_id,
        actor_type="user",
        actor_id=token.sub,
        action="settings.retention.updated",
        target_type="tenant_settings",
        target_id=token.tenant_id,
        before=before,
        after=after
    )
    
    return {"success": True}


# ============================================================================
# /api/audit - Audit Logs
# ============================================================================

class AuditLogResponse(BaseModel):
    id: UUID
    actor_type: str
    actor_id: Optional[str]
    action: str
    target_type: str
    target_id: str
    reason: Optional[str]
    confidence: Optional[float]
    before: Optional[dict]
    after: Optional[dict]
    occurred_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/audit", response_model=List[AuditLogResponse], tags=["audit"])
async def list_audit_logs(
    actor_type: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    token: TokenPayload = Depends(verify_token)
):
    """List audit log entries"""
    async with get_tenant_session(token.tenant_id) as session:
        query = select(AuditLog).order_by(AuditLog.occurred_at.desc())
        
        if actor_type:
            query = query.where(AuditLog.actor_type == actor_type)
        if action:
            query = query.where(AuditLog.action == action)
        if target_type:
            query = query.where(AuditLog.target_type == target_type)
        
        query = query.limit(limit).offset(offset)
        result = await session.execute(query)
        logs = result.scalars().all()
        return logs


@router.get("/audit/{log_id}", response_model=AuditLogResponse, tags=["audit"])
async def get_audit_log(
    log_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Get a specific audit log entry"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        return log
