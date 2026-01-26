"""
AFASA 2.0 Common Library
"""
from .settings import get_settings, Settings
from .auth import verify_token, require_role, TokenPayload
from .db import get_tenant_session, get_admin_session, Base, init_db
from .models import (
    Tenant, User, TenantSettings, Camera, Snapshot, Detection,
    Assessment, Task, RuleProposal, Report, TelegramLink, Secret, AuditLog
)
from .events import get_event_bus, EventBus, EventEnvelope, Subjects
from .s3 import get_storage_client, StorageClient
from .secrets import get_secrets_manager, SecretsManager
from .audit import get_audit_service, AuditService
from .rate_limiter import get_rate_limiter, RateLimiter
from .health import create_health_router, record_request, RequestTimer

__all__ = [
    "get_settings", "Settings",
    "verify_token", "require_role", "TokenPayload",
    "get_tenant_session", "get_admin_session", "Base", "init_db",
    "Tenant", "User", "TenantSettings", "Camera", "Snapshot", "Detection",
    "Assessment", "Task", "RuleProposal", "Report", "TelegramLink", "Secret", "AuditLog",
    "get_event_bus", "EventBus", "EventEnvelope", "Subjects",
    "get_storage_client", "StorageClient",
    "get_secrets_manager", "SecretsManager",
    "get_audit_service", "AuditService",
    "get_rate_limiter", "RateLimiter",
    "create_health_router", "record_request", "RequestTimer"
]
