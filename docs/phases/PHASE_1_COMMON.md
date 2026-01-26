# Phase 1: Operational Hardening (A-H)

> **Status**: FIRST BUILD PRIORITY
> **Prerequisite**: Phase 0 complete (architecture frozen)
> **Duration**: 1-2 weeks

---

## Objective

Implement all operational hardening measures (A-H) to establish an operationally safe baseline.

---

## Overview

| Item | Priority | Status |
|------|----------|--------|
| A) Secrets Management | Critical | ⬜ |
| B) Tenant Bootstrap | Critical | ⬜ |
| C) Audit Log | Critical | ⬜ |
| D) Data Retention | High | ⬜ |
| E) Rate Limiting | High | ⬜ |
| F) Observability | High | ⬜ |
| G) UTC Time | Medium | ⬜ |
| H) RS485 Documentation | Medium | ⬜ |

---

## A) Secrets Management

### Requirements
- No plaintext credentials in database
- All credentials referenced via `secret_ref`
- Encryption at rest using master key

### Implementation Tasks

1. **Create secrets table**
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
   ```

2. **Implement encryption service** in `services/common/`
   - Use Fernet symmetric encryption
   - Master key from `AFASA_MASTER_KEY_BASE64` env var

3. **Create secrets API endpoints**
   - `POST /api/secrets` - Store secret
   - `GET /api/secrets/{name}` - Retrieve (internal only)
   - `POST /api/secrets/{name}/rotate` - Rotate secret

4. **Update all services** to use secret_ref pattern

### Verification
- [ ] No plaintext credentials in DB
- [ ] All creds referenced via secret_ref
- [ ] Rotation works

---

## B) Tenant Bootstrap

### Requirements
- Atomic tenant + user + settings creation
- Keycloak user has `tenant_id` attribute
- No orphan entities possible

### Implementation Tasks

1. **Create provisioning service** or endpoint
   ```
   services/provisioning/
   ├── Dockerfile
   ├── main.py
   └── routes/
       └── tenant.py
   ```

2. **Implement atomic creation**
   - Database transaction for tenant + settings
   - Keycloak API call for user creation
   - Rollback on any failure

3. **Add to docker-compose.yml**

### Verification
- [ ] Tenant + user + settings created atomically
- [ ] Keycloak JWT includes `tenant_id`
- [ ] Rollback on partial failure

---

## C) Audit Log

### Requirements
- Append-only log (no updates, no deletes)
- Every action logged with context
- AI entries include reason + confidence

### Implementation Tasks

1. **Create audit_log table**
   ```sql
   CREATE TABLE audit_log (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       tenant_id UUID NOT NULL,
       timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       actor_type VARCHAR(50) NOT NULL,
       actor_id VARCHAR(255),
       action VARCHAR(100) NOT NULL,
       resource_type VARCHAR(100) NOT NULL,
       resource_id UUID,
       before_state JSONB,
       after_state JSONB,
       reason TEXT,
       confidence DECIMAL(5,4),
       request_id UUID
   );

   REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
   ```

2. **Create audit service** in `services/common/`

3. **Add audit calls** to all mutation operations

### Verification
- [ ] Every rule/task/action logged
- [ ] AI entries include reason + confidence
- [ ] Append-only enforced

---

## D) Data Retention

### Requirements
- MinIO keys prefixed by tenant
- Daily cleanup job
- Respect tenant TTL settings

### Implementation Tasks

1. **Update MinIO key structure**
   ```
   tenant/{tenant_id}/snapshots/raw/{date}/{id}.jpg
   tenant/{tenant_id}/snapshots/annotated/{date}/{id}.jpg
   tenant/{tenant_id}/reports/{month}/{id}.pdf
   ```

2. **Create retention cleaner service**
   ```
   services/retention_cleaner/
   ├── Dockerfile
   ├── main.py
   └── cleanup.py
   ```

3. **Add cron job** (runs daily at 2 AM UTC)

### Verification
- [ ] MinIO keys prefixed by tenant
- [ ] Cleanup job runs
- [ ] Tenant TTL respected

---

## E) Rate Limiting

### Requirements
- Per-tenant rate limits
- Cooldown between similar alerts
- Quiet hours respected

### Implementation Tasks

1. **Add Redis keys**
   ```
   afasa:alerts:{tenant_id}:count
   afasa:alerts:{tenant_id}:last:{type}
   ```

2. **Implement RateLimiter class** in `services/common/`

3. **Integrate with Telegram service**

### Verification
- [ ] Telegram cooldown enforced
- [ ] Quiet hours respected
- [ ] Skipped alerts logged

---

## F) Observability

### Requirements
- Health endpoints on all services
- Prometheus metrics
- Structured logging with context

### Implementation Tasks

1. **Add to each service's main.py**
   ```python
   @app.get("/healthz")
   async def liveness():
       return {"status": "ok"}

   @app.get("/readyz")
   async def readiness():
       # Check dependencies
       return {"status": "ready"}

   @app.get("/metrics")
   async def metrics():
       # Prometheus format
   ```

2. **Update requirements.txt** with prometheus-client

3. **Create prometheus.yml** in `deploy/prometheus/`

4. **Add Grafana dashboards** (optional)

### Verification
- [ ] /healthz exists on all services
- [ ] /readyz exists on all services
- [ ] /metrics exposed
- [ ] Logs include tenant_id + request_id

---

## G) UTC Time

### Requirements
- NTP enabled
- Database timestamps in UTC
- ISO8601 format in events

### Implementation Tasks

1. **Docker Compose** - add `TZ: UTC` to all services

2. **Database** - ensure TIMESTAMPTZ used everywhere

3. **Code** - use UTC utility function
   ```python
   from datetime import datetime, timezone
   
   def utc_now():
       return datetime.now(timezone.utc)
   ```

### Verification
- [ ] NTP enabled
- [ ] DB timestamps UTC
- [ ] ISO8601 in events

---

## H) RS485 Documentation

### Requirements
- No direct RS485 code paths
- Document the limitation
- Telemetry via gateway only

### Implementation Tasks

1. **Add to architecture docs**

2. **Update device integration docs**

### Verification
- [ ] No RS485/serial imports
- [ ] Documented limitation

---

## Deliverables

1. Secrets encryption working
2. Provisioning endpoint functional
3. Audit log capturing all actions
4. Retention cleanup running
5. Rate limiting active
6. Observability endpoints exposed
7. UTC standardized
8. RS485 documented

---

## References

- [Operational Hardening Details](../OPERATIONAL_HARDENING.md)
- [MVP Acceptance Checklist](../MVP_ACCEPTANCE_CHECKLIST.md)
