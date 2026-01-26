# Phase 0: Architecture Freeze

> **Status**: REQUIRED BEFORE ALL OTHER PHASES
> **Duration**: 1-2 days

---

## Objective

Confirm and freeze all architectural decisions before implementation begins.

---

## 1) Service Boundaries (Confirm Unchanged)

| Service | Responsibility | Status |
|---------|---------------|--------|
| `traefik` | Edge routing, TLS termination | ⬜ |
| `postgres` | Multi-tenant data, RLS enforced | ⬜ |
| `redis` | Rate limiting, cooldowns, caching | ⬜ |
| `nats` | Event bus with JetStream | ⬜ |
| `minio` | S3-compatible blob storage | ⬜ |
| `keycloak` | Identity, OIDC, tenant_id claims | ⬜ |
| `mediamtx` | RTSP→HLS transcoding | ⬜ |
| `afasa-media` | Snapshot capture, video source registry | ⬜ |
| `afasa-vision-yolo` | YOLO inference on snapshots | ⬜ |
| `afasa-vision-reasoner` | AI reasoning (Gemini/GPT) | ⬜ |
| `afasa-ops` | Policy gate, task management, scheduler | ⬜ |
| `afasa-telegram` | Notification delivery, bot commands | ⬜ |
| `afasa-report` | PDF/XLSX generation | ⬜ |
| `afasa-tb-adapter` | ThingsBoard sync, embed tokens, rulechains | ⬜ |
| `afasa-portal` | Thin control-plane frontend | ⬜ |

---

## 2) Tenant Isolation (Confirm Enforced)

### Postgres RLS
```sql
-- Every table with tenant data
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON table_name
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Confirm:**
- [ ] All tenant tables have RLS enabled
- [ ] Session variable `app.tenant_id` set on every request
- [ ] No cross-tenant data leakage possible

### MinIO Key Prefix
```
tenant/{tenant_id}/snapshots/...
tenant/{tenant_id}/reports/...
```

**Confirm:**
- [ ] All object keys include tenant prefix
- [ ] Access policies enforce prefix isolation

### JWT Claims
```json
{
  "tenant_id": "uuid",
  "roles": ["tenant_admin"]
}
```

**Confirm:**
- [ ] Keycloak includes `tenant_id` in access token
- [ ] API Gateway extracts and validates claim

---

## 3) Event Naming (Confirm Versioned)

| Event | Version | Publisher |
|-------|---------|-----------|
| `afasa.media.v1.snapshot.captured` | v1 | media |
| `afasa.vision.v1.yolo.completed` | v1 | yolo |
| `afasa.vision.v1.assessment.created` | v1 | reasoner |
| `afasa.ops.v1.task.created` | v1 | ops |
| `afasa.ops.v1.rule.proposed` | v1 | reasoner |
| `afasa.ops.v1.rule.approved` | v1 | ops |
| `afasa.ops.v1.rule.rejected` | v1 | ops |
| `afasa.report.v1.ready` | v1 | report |
| `afasa.alert.v1.sent` | v1 | telegram |

**Confirm:**
- [ ] All events follow naming convention
- [ ] Version number allows future breaking changes
- [ ] NATS JetStream streams configured

---

## 4) API Gateway Pattern (Confirm)

```
[External Request]
        │
        ▼
    [Traefik]
        │
        ▼
  [API Gateway (FastAPI)]
        │
        ├── JWT validation
        ├── tenant_id extraction
        ├── Rate limiting
        └── Routing to internal services
        │
        ▼
  [Internal Services]
```

**Confirm:**
- [ ] All external requests go through API Gateway
- [ ] No direct external access to internal services
- [ ] Internal services trust gateway's tenant_id header

---

## 5) Database Schema (Confirm)

### Core Tables Required

```sql
-- Identity
tenants
tenant_settings
users

-- Secrets
secrets (encrypted credentials)

-- Devices
devices
video_sources

-- Vision
snapshots
yolo_results
assessments

-- Operations
tasks
rules
rule_proposals

-- Governance
audit_log

-- Reports
reports
```

**Confirm:**
- [ ] Schema file exists in `infra/postgres/init/`
- [ ] All tables include `tenant_id`
- [ ] RLS policies defined

---

## Deliverables

1. **Architecture freeze note** (this document, signed off)
2. **API list** (see [API_CONTRACT.md](./API_CONTRACT.md))
3. **Event list** (table above)

---

## Verification Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 0.1 | Service boundaries unchanged | ⬜ |
| 0.2 | `tenant_id` enforced everywhere | ⬜ |
| 0.3 | Event names versioned | ⬜ |
| 0.4 | No direct service coupling | ⬜ |

**FAIL if:** Any service bypasses API gateway for external requests.

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Architect | | | |
| Lead Dev | | | |

---

## References

- [Master Architecture](../MASTER_ARCHITECTURE.md)
- [API Contract](../API_CONTRACT.md)
