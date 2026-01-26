# AFASA 2.0 - MASTER ARCHITECTURE SPECIFICATION (FROZEN)

> **Document Status**: FROZEN - Do not change service boundaries
> **Last Updated**: 2026-01-21

---

## 0) Non-Negotiable Boundary

**AFASA 2.0 core architecture is frozen.**

- ❌ Do NOT change service boundaries
- ❌ Do NOT rebuild TB charts/widgets in React
- ❌ Do NOT stream RTSP in the browser directly
- ❌ Do NOT store camera credentials in frontend
- ❌ Do NOT embed TB admin session; use short-lived tokens only

**ThingsBoard** remains the primary visualization/telemetry layer.
The **Personal Web App** is a thin control-plane UI, not a full dashboard engine.
The web app embeds TB dashboards and adds AFASA widgets for AI context, approvals, and onboarding.

---

## 1) Service Boundaries (Frozen)

| Service | Responsibility | Dependencies |
|---------|---------------|--------------|
| `traefik` | Edge routing, TLS termination | - |
| `postgres` | Multi-tenant data, RLS enforced | - |
| `redis` | Rate limiting, cooldowns, caching | - |
| `nats` | Event bus with JetStream | - |
| `minio` | S3-compatible blob storage | - |
| `keycloak` | Identity, OIDC, tenant_id claims | postgres |
| `mediamtx` | RTSP→HLS transcoding | - |
| `afasa-media` | Snapshot capture, video source registry | postgres, nats, minio, mediamtx |
| `afasa-vision-yolo` | YOLO inference on snapshots | postgres, nats, redis, minio |
| `afasa-vision-reasoner` | AI reasoning (Gemini/GPT) | postgres, nats, minio |
| `afasa-ops` | Policy gate, task management, scheduler | postgres, nats, redis |
| `afasa-telegram` | Notification delivery, bot commands | postgres, nats, redis |
| `afasa-report` | PDF/XLSX generation | postgres, nats, minio |
| `afasa-tb-adapter` | ThingsBoard sync, embed tokens, rulechains | postgres, nats |
| `afasa-portal` | Thin control-plane frontend | keycloak, api-gateway |

---

## 2) API Gateway Pattern

All frontend API calls **MUST** go through AFASA API Gateway (FastAPI).

The API Gateway is responsible for:
1. Verifying JWT (from Keycloak)
2. Tenant context extraction (`tenant_id` claim)
3. Minting TB embed tokens
4. Generating MinIO signed URLs

**Frontend ↔ Backend Flow:**
```
[Portal] → [API Gateway] → [Internal Services]
              ↓
         JWT Validation
         Tenant Extraction
         Rate Limiting
```

---

## 3) Multi-Tenancy Model

### Tenant Isolation
- Postgres RLS enforced via `app.tenant_id` session variable
- All tables include `tenant_id` column
- MinIO keys prefixed: `tenant/{tenant_id}/...`

### JWT Structure
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "roles": ["tenant_admin"],
  "aud": "afasa-api",
  "iss": "https://auth.afasa.io/realms/afasa"
}
```

---

## 4) Event-Driven Architecture

### Event Naming Convention
```
afasa.{domain}.{version}.{action}
```

### Core Events
| Event | Publisher | Subscribers |
|-------|-----------|-------------|
| `afasa.media.v1.snapshot.captured` | media | yolo, ops |
| `afasa.vision.v1.yolo.completed` | yolo | reasoner, ops |
| `afasa.vision.v1.assessment.created` | reasoner | ops, telegram |
| `afasa.ops.v1.task.created` | ops | telegram |
| `afasa.ops.v1.rule.proposed` | reasoner | ops |
| `afasa.ops.v1.rule.approved` | ops | tb-adapter |
| `afasa.ops.v1.rule.rejected` | ops | audit |

---

## 5) Data Model Summary

### Core Tables
```sql
tenants              -- Tenant registry
tenant_settings      -- Retention, AI policy, alert config
users                -- User accounts (synced from Keycloak)
secrets              -- Encrypted credentials (secret_ref pattern)
devices              -- Unified device registry (cameras, nvr, iot)
video_sources        -- RTSP/HLS stream configurations
snapshots            -- Captured frames metadata
assessments          -- AI reasoning outputs
tasks                -- Generated action items
rules                -- Active automation rules
rule_proposals       -- Pending AI-proposed rules
audit_log            -- Append-only action log
reports              -- Generated report metadata
```

---

## 6) Security Invariants

1. **No plaintext credentials** in database
2. **All creds referenced via `secret_ref`**
3. **Audit log is append-only**
4. **AI proposals require approval before execution**
5. **Rate limiting enforced for external notifications**
6. **UTC timestamps everywhere**
7. **RS485 only via gateway (no direct integration)**

---

## 7) Observability Requirements

Every service MUST expose:
- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe  
- `GET /metrics` - Prometheus metrics

All logs MUST include:
- `tenant_id`
- `request_id` (correlation ID)
- UTC timestamp

---

## References

- [Frontend Specification](./FRONTEND_SPEC.md)
- [API Contract Table](./API_CONTRACT.md)
- [Operational Hardening A-H](./OPERATIONAL_HARDENING.md)
- [MVP Acceptance Checklist](./MVP_ACCEPTANCE_CHECKLIST.md)
