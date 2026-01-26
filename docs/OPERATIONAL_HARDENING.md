# AFASA 2.0 - OPERATIONAL HARDENING (A-H)

> **Document Status**: MUST IMPLEMENT
> **Last Updated**: 2026-01-21
> **Phase**: 1 (First Build Priority)

---

## Overview

AFASA 2.0 core architecture is **frozen**. Add the following operational hardening measures **without changing service boundaries**.

---

## A) Secrets Management

### Requirements
- ❌ **No plaintext credentials in database**
- ✅ All credentials referenced via `secret_ref` pattern
- ✅ Encryption at rest using `AFASA_MASTER_KEY_BASE64`

### Implementation

**Database Schema:**
```sql
CREATE TABLE secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    encrypted_value BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Enable RLS
ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON secrets
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Encryption:**
```python
import base64
from cryptography.fernet import Fernet

# Master key from environment
MASTER_KEY = base64.b64decode(os.environ["AFASA_MASTER_KEY_BASE64"])
fernet = Fernet(base64.urlsafe_b64encode(MASTER_KEY[:32]))

def encrypt_secret(plaintext: str) -> bytes:
    return fernet.encrypt(plaintext.encode())

def decrypt_secret(ciphertext: bytes) -> str:
    return fernet.decrypt(ciphertext).decode()
```

**Usage Pattern:**
```python
# Storing credential
secret_ref = secrets_service.store(
    tenant_id=tenant_id,
    name="rtsp_cam_01",
    value="rtsp://user:pass@192.168.1.100:554/stream"
)
# Returns: "secret:rtsp_cam_01"

# Retrieving credential
credential = secrets_service.get(tenant_id, "rtsp_cam_01")
```

### Rotation
```python
async def rotate_secret(tenant_id: UUID, name: str, new_value: str) -> str:
    # 1. Store new value
    # 2. Update references
    # 3. Log to audit
    # 4. Return new secret_ref
```

### Verification Checklist
- [ ] No plaintext credentials in DB
- [ ] All creds referenced via secret_ref
- [ ] Rotation works
- [ ] Audit log entry on rotation

---

## B) Tenant Bootstrap

### Requirements
- ✅ Tenant + user + settings created **atomically**
- ✅ Keycloak user has `tenant_id` attribute
- ✅ No orphan tenants or users

### Implementation

**Provisioning Service Endpoint:**
```python
@router.post("/api/provisioning/tenant")
async def create_tenant(request: CreateTenantRequest):
    """
    Atomic tenant creation:
    1. Create Postgres tenant + settings
    2. Create Keycloak user with tenant_id attribute
    3. (Optional) Create ThingsBoard tenant
    """
    async with db.transaction():
        # 1. Create tenant
        tenant = await db.execute("""
            INSERT INTO tenants (id, name)
            VALUES ($1, $2)
            RETURNING id
        """, [uuid4(), request.name])
        
        # 2. Create default settings
        await db.execute("""
            INSERT INTO tenant_settings (tenant_id, ...)
            VALUES ($1, ...)
        """, [tenant.id, ...])
        
        # 3. Create Keycloak user
        await keycloak.create_user(
            realm="afasa",
            user={
                "username": request.admin_email,
                "email": request.admin_email,
                "enabled": True,
                "attributes": {
                    "tenant_id": [str(tenant.id)]
                }
            }
        )
        
        # 4. Assign role
        await keycloak.assign_role(user_id, "tenant_admin")
        
    return {"tenant_id": tenant.id}
```

### Verification Checklist
- [ ] Tenant + user + settings created atomically
- [ ] Keycloak JWT includes `tenant_id`
- [ ] Rollback on partial failure

---

## C) Audit Log

### Requirements
- ✅ **Append-only** log (no updates, no deletes)
- ✅ Every rule/task/action logged
- ✅ AI entries include `reason` + `confidence`

### Implementation

**Database Schema:**
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type VARCHAR(50) NOT NULL, -- 'user', 'ai', 'system'
    actor_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    before_state JSONB,
    after_state JSONB,
    reason TEXT,
    confidence DECIMAL(5,4),
    request_id UUID,
    ip_address INET,
    user_agent TEXT
);

-- No UPDATE or DELETE allowed
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE ON audit_log FROM afasa;

-- Index for queries
CREATE INDEX idx_audit_tenant_time ON audit_log(tenant_id, timestamp DESC);
CREATE INDEX idx_audit_action ON audit_log(action);
```

**Service:**
```python
class AuditService:
    async def log(
        self,
        tenant_id: UUID,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: UUID = None,
        before_state: dict = None,
        after_state: dict = None,
        reason: str = None,
        confidence: float = None,
        request_id: UUID = None
    ):
        await self.db.execute("""
            INSERT INTO audit_log (...)
            VALUES (...)
        """, [...])
```

### Actions to Log
| Action | When |
|--------|------|
| `rule.proposed` | AI proposes new rule |
| `rule.approved` | User approves proposal |
| `rule.rejected` | User rejects proposal |
| `rule.created` | New rule activated |
| `task.created` | Task generated |
| `task.completed` | Task marked done |
| `device.added` | New device registered |
| `device.removed` | Device deleted |
| `settings.updated` | Settings changed |
| `secret.rotated` | Credential rotated |
| `alert.sent` | Notification sent |
| `alert.skipped` | Alert rate-limited |

### Verification Checklist
- [ ] Every rule/task/action logged
- [ ] AI entries include reason + confidence
- [ ] Append-only enforced (no UPDATE/DELETE)

---

## D) Data Retention

### Requirements
- ✅ MinIO keys prefixed by tenant: `tenant/{tenant_id}/...`
- ✅ Cleanup job runs daily
- ✅ Tenant TTL respected

### Implementation

**MinIO Key Structure:**
```
tenant/{tenant_id}/snapshots/raw/{YYYY-MM-DD}/{uuid}.jpg
tenant/{tenant_id}/snapshots/annotated/{YYYY-MM-DD}/{uuid}.jpg
tenant/{tenant_id}/reports/{YYYY-MM}/{uuid}.pdf
```

**Cleanup Job (Daily Cron):**
```python
@scheduler.cron("0 2 * * *")  # 2 AM UTC daily
async def cleanup_expired_data():
    tenants = await db.fetch("SELECT id FROM tenants")
    
    for tenant in tenants:
        settings = await get_tenant_settings(tenant.id)
        
        # Calculate cutoff dates
        snapshot_cutoff = now() - timedelta(days=settings.retention_snapshots_days)
        report_cutoff = now() - timedelta(days=settings.retention_reports_days)
        
        # Delete old snapshots from MinIO
        await minio.delete_older_than(
            prefix=f"tenant/{tenant.id}/snapshots/",
            cutoff=snapshot_cutoff
        )
        
        # Delete old reports
        await minio.delete_older_than(
            prefix=f"tenant/{tenant.id}/reports/",
            cutoff=report_cutoff
        )
        
        # Clean database records
        await db.execute("""
            DELETE FROM snapshots 
            WHERE tenant_id = $1 AND created_at < $2
        """, [tenant.id, snapshot_cutoff])
```

### Verification Checklist
- [ ] MinIO keys prefixed by tenant
- [ ] Cleanup job runs (check logs)
- [ ] Tenant TTL respected
- [ ] Audit log of deletions

---

## E) Alert Rate Limiting

### Requirements
- ✅ Per-tenant rate limiting
- ✅ Cooldown between similar alerts
- ✅ Quiet hours respected
- ✅ Skipped alerts logged

### Implementation

**Redis Keys:**
```
afasa:alerts:{tenant_id}:count          # Daily counter
afasa:alerts:{tenant_id}:last:{type}    # Last alert timestamp by type
```

**Rate Limiter:**
```python
class AlertRateLimiter:
    async def should_send(
        self,
        tenant_id: UUID,
        alert_type: str,
        settings: TenantSettings
    ) -> tuple[bool, str]:
        now = datetime.utcnow()
        
        # Check quiet hours
        if self._in_quiet_hours(now, settings):
            return False, "quiet_hours"
        
        # Check daily limit
        daily_count = await redis.get(f"afasa:alerts:{tenant_id}:count")
        if daily_count >= settings.max_daily_alerts:
            return False, "daily_limit"
        
        # Check cooldown
        last_sent = await redis.get(f"afasa:alerts:{tenant_id}:last:{alert_type}")
        if last_sent:
            elapsed = (now - last_sent).total_seconds() / 60
            if elapsed < settings.cooldown_minutes:
                return False, "cooldown"
        
        return True, None
    
    async def record_sent(self, tenant_id: UUID, alert_type: str):
        await redis.incr(f"afasa:alerts:{tenant_id}:count")
        await redis.set(
            f"afasa:alerts:{tenant_id}:last:{alert_type}",
            datetime.utcnow().isoformat()
        )

    def _in_quiet_hours(self, now: datetime, settings: TenantSettings) -> bool:
        current_time = now.time()
        start = time.fromisoformat(settings.quiet_hours_start)
        end = time.fromisoformat(settings.quiet_hours_end)
        
        if start <= end:
            return start <= current_time <= end
        else:  # Overnight quiet hours (e.g., 22:00 - 06:00)
            return current_time >= start or current_time <= end
```

### Verification Checklist
- [ ] Telegram cooldown enforced
- [ ] Quiet hours respected
- [ ] Skipped alerts logged to audit
- [ ] Daily limit enforced

---

## F) Observability

### Requirements
- ✅ `/healthz` endpoint (liveness)
- ✅ `/readyz` endpoint (readiness)
- ✅ `/metrics` exposed (Prometheus format)
- ✅ Logs include `tenant_id` + `request_id`

### Implementation

**Health Endpoints (FastAPI):**
```python
@router.get("/healthz")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "ok"}

@router.get("/readyz")
async def readiness(db: Database = Depends(get_db)):
    """Kubernetes readiness probe"""
    try:
        await db.execute("SELECT 1")
        return {"status": "ready", "db": "connected"}
    except Exception:
        raise HTTPException(503, "Not ready")

@router.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return Response(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

# Middleware to add context
@app.middleware("http")
async def add_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    tenant_id = getattr(request.state, "tenant_id", None)
    
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        tenant_id=str(tenant_id) if tenant_id else None
    )
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "afasa_requests_total",
    "Total requests",
    ["service", "method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "afasa_request_latency_seconds",
    "Request latency",
    ["service", "endpoint"]
)
```

### Verification Checklist
- [ ] `/healthz` exists on all services
- [ ] `/readyz` exists on all services
- [ ] `/metrics` exposed on all services
- [ ] Logs include tenant_id + request_id

---

## G) UTC Time Standardization

### Requirements
- ✅ NTP enabled on all hosts
- ✅ Database timestamps in UTC
- ✅ Events use ISO8601 format

### Implementation

**Database Default:**
```sql
-- All timestamp columns use TIMESTAMPTZ
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

-- Ensure UTC timezone
SET timezone = 'UTC';
```

**Python Service:**
```python
from datetime import datetime, timezone

# Always use UTC
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# ISO8601 formatting
def to_iso8601(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")
```

**Docker Compose:**
```yaml
services:
  every-service:
    environment:
      TZ: UTC
```

**NTP Configuration:**
```bash
# Ensure NTP is enabled on host
timedatectl set-ntp true
```

### Verification Checklist
- [ ] NTP enabled on host
- [ ] DB timestamps in UTC
- [ ] ISO8601 in all events
- [ ] TZ=UTC in all containers

---

## H) RS485 via Gateway Only

### Requirements
- ❌ No direct RS485 code paths in AFASA services
- ✅ Telemetry only via gateway (UbiBot GS1) or cloud API
- ✅ Documented limitation

### Implementation

**Documented Architecture:**
```
┌──────────────────────────────────────────────────────┐
│                    AFASA Services                     │
│                  (No RS485 drivers)                   │
└──────────────────────────────────────────────────────┘
                          │
                          │ HTTP/MQTT
                          ▼
┌──────────────────────────────────────────────────────┐
│                  UbiBot Cloud API                     │
│              OR  UbiBot GS1 Gateway                   │
└──────────────────────────────────────────────────────┘
                          │
                          │ RS485
                          ▼
┌──────────────────────────────────────────────────────┐
│                   RS485 Sensors                       │
│              (Soil, pH, EC, etc.)                     │
└──────────────────────────────────────────────────────┘
```

**Why:**
- RS485 requires physical serial connection
- AFASA runs in Docker containers (no serial access)
- UbiBot GS1 handles RS485↔IP translation
- Cloud API provides telemetry data

### Verification Checklist
- [ ] No RS485/serial imports in codebase
- [ ] Telemetry fetched via HTTP API only
- [ ] Documentation includes this limitation

---

## Summary Table

| Item | Priority | Verification |
|------|----------|--------------|
| A) Secrets | Critical | No plaintext in DB, rotation works |
| B) Bootstrap | Critical | Atomic tenant creation |
| C) Audit | Critical | Append-only, AI entries have reason |
| D) Retention | High | Daily cleanup runs |
| E) Rate Limiting | High | Cooldown enforced |
| F) Observability | High | All endpoints exposed |
| G) UTC | Medium | All timestamps UTC |
| H) RS485 | Medium | Documented, no direct code |

---

## References

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [MVP Acceptance Checklist](./MVP_ACCEPTANCE_CHECKLIST.md)
