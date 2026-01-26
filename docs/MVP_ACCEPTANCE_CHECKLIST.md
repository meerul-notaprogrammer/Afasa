# AFASA 2.0 - MVP ACCEPTANCE TEST CHECKLIST (PASS/FAIL)

> **Document Status**: STRICT PASS/FAIL CRITERIA
> **Last Updated**: 2026-01-21
> **Purpose**: This is how you know when a phase is DONE.

---

## PHASE 0 — Architecture Freeze

| # | Criterion | Status |
|---|-----------|--------|
| 0.1 | Service boundaries unchanged | ⬜ |
| 0.2 | `tenant_id` enforced everywhere (RLS active) | ⬜ |
| 0.3 | Event names versioned (e.g., `afasa.media.v1.snapshot.captured`) | ⬜ |
| 0.4 | No new direct service coupling (all via NATS or API gateway) | ⬜ |

**FAIL if:** Any service bypasses API gateway for external requests.

**Deliverable:** Architecture freeze note + API list

---

## PHASE 1 — Operational Hardening (A–H)

### A) Secrets Management

| # | Criterion | Status |
|---|-----------|--------|
| 1.A.1 | No plaintext credentials in database | ⬜ |
| 1.A.2 | All credentials referenced via `secret_ref` | ⬜ |
| 1.A.3 | Secret rotation works (POST `/api/secrets/rotate`) | ⬜ |
| 1.A.4 | Audit log entry created on rotation | ⬜ |

### B) Tenant Bootstrap

| # | Criterion | Status |
|---|-----------|--------|
| 1.B.1 | Tenant + user + settings created atomically | ⬜ |
| 1.B.2 | Keycloak JWT includes `tenant_id` claim | ⬜ |
| 1.B.3 | Transaction rollback on partial failure | ⬜ |
| 1.B.4 | No orphan tenants or users possible | ⬜ |

### C) Audit Log

| # | Criterion | Status |
|---|-----------|--------|
| 1.C.1 | Every rule/task/action logged | ⬜ |
| 1.C.2 | AI entries include `reason` + `confidence` fields | ⬜ |
| 1.C.3 | Append-only enforced (UPDATE/DELETE revoked) | ⬜ |
| 1.C.4 | Audit query endpoint works (`/api/audit`) | ⬜ |

### D) Data Retention

| # | Criterion | Status |
|---|-----------|--------|
| 1.D.1 | MinIO keys prefixed by tenant (`tenant/{id}/...`) | ⬜ |
| 1.D.2 | Cleanup job runs daily (verify logs) | ⬜ |
| 1.D.3 | Tenant TTL settings respected | ⬜ |
| 1.D.4 | Expired snapshots/reports deleted | ⬜ |

### E) Rate Limiting

| # | Criterion | Status |
|---|-----------|--------|
| 1.E.1 | Telegram cooldown enforced | ⬜ |
| 1.E.2 | Quiet hours respected (no alerts during window) | ⬜ |
| 1.E.3 | Skipped alerts logged to audit | ⬜ |
| 1.E.4 | Daily alert limit enforced | ⬜ |

### F) Observability

| # | Criterion | Status |
|---|-----------|--------|
| 1.F.1 | `/healthz` exists on all services | ⬜ |
| 1.F.2 | `/readyz` exists on all services | ⬜ |
| 1.F.3 | `/metrics` exposed on all services | ⬜ |
| 1.F.4 | Logs include `tenant_id` + `request_id` | ⬜ |
| 1.F.5 | Prometheus can scrape all metrics | ⬜ |

### G) UTC Time

| # | Criterion | Status |
|---|-----------|--------|
| 1.G.1 | NTP enabled on host | ⬜ |
| 1.G.2 | Database timestamps in UTC (TIMESTAMPTZ) | ⬜ |
| 1.G.3 | All events use ISO8601 format | ⬜ |
| 1.G.4 | `TZ=UTC` in all container environments | ⬜ |

### H) RS485

| # | Criterion | Status |
|---|-----------|--------|
| 1.H.1 | No direct RS485 code paths in services | ⬜ |
| 1.H.2 | Telemetry only via gateway/cloud API | ⬜ |
| 1.H.3 | Limitation documented | ⬜ |

**FAIL if:** Any AI action lacks audit record.

**Deliverable:** Operationally safe baseline

---

## PHASE 2 — Vision Core

| # | Criterion | Status |
|---|-----------|--------|
| 2.1 | RTSP snapshot capture works (frame extracted from stream) | ⬜ |
| 2.2 | Snapshots stored in MinIO with tenant prefix | ⬜ |
| 2.3 | YOLO inference runs on snapshots (not live stream) | ⬜ |
| 2.4 | Confidence + bounding box returned in response | ⬜ |
| 2.5 | Annotated images generated (optional, configurable) | ⬜ |
| 2.6 | Reasoner runs on curated snapshots | ⬜ |
| 2.7 | Reasoner assessment includes severity, confidence, actions | ⬜ |
| 2.8 | Tasks generated from assessments | ⬜ |
| 2.9 | Telegram summary notifications sent | ⬜ |
| 2.10 | Event published: `afasa.media.v1.snapshot.captured` | ⬜ |
| 2.11 | Event published: `afasa.vision.v1.yolo.completed` | ⬜ |
| 2.12 | Event published: `afasa.vision.v1.assessment.created` | ⬜ |

**FAIL if:** YOLO runs on full live stream (must be snapshot-only).

**Deliverable:** End-to-end AI monitoring

---

## PHASE 3 — Governance + ThingsBoard

| # | Criterion | Status |
|---|-----------|--------|
| 3.1 | TB Adapter syncs devices to ThingsBoard | ⬜ |
| 3.2 | Embed token minting works (`/api/tb/embed-token`) | ⬜ |
| 3.3 | TB dashboard lists available via API | ⬜ |
| 3.4 | Rule proposals stored in database | ⬜ |
| 3.5 | Rule approval creates TB rulechain OR activates AFASA policy | ⬜ |
| 3.6 | Rule rejection leaves system unchanged | ⬜ |
| 3.7 | All approval/rejection actions audited | ⬜ |
| 3.8 | Protected devices cannot be modified by AI | ⬜ |
| 3.9 | Dashboard template selection works | ⬜ |

**FAIL if:** Rules auto-activate without policy gate / human approval.

**Deliverable:** Governed automation + real dashboards

---

## PHASE 4 — Personal Web App

### Authentication & Layout

| # | Criterion | Status |
|---|-----------|--------|
| 4.1 | Keycloak login works (PKCE flow) | ⬜ |
| 4.2 | User lands on dashboard without manual tenant select | ⬜ |
| 4.3 | App shell renders (sidebar, topbar, content area) | ⬜ |
| 4.4 | Tenant name displayed in header | ⬜ |
| 4.5 | `/api/me` returns correct tenant context | ⬜ |

### Main Dashboard

| # | Criterion | Status |
|---|-----------|--------|
| 4.6 | ThingsBoard dashboard embeds correctly (iframe) | ⬜ |
| 4.7 | Snapshot gallery shows latest snapshots | ⬜ |
| 4.8 | Tasks section shows today's tasks | ⬜ |
| 4.9 | Pending approvals section visible | ⬜ |
| 4.10 | AI assessments panel shows latest | ⬜ |

### Devices

| # | Criterion | Status |
|---|-----------|--------|
| 4.11 | Device list loads | ⬜ |
| 4.12 | Camera can be added (RTSP URL) | ⬜ |
| 4.13 | NVR can be added | ⬜ |
| 4.14 | UbiBot can be connected (API key) | ⬜ |
| 4.15 | UbiBot sync populates devices | ⬜ |
| 4.16 | ThingsBoard can be connected | ⬜ |
| 4.17 | Device enable/disable works | ⬜ |

### Rules & Approvals

| # | Criterion | Status |
|---|-----------|--------|
| 4.18 | Active rules list loads | ⬜ |
| 4.19 | Pending proposals list loads | ⬜ |
| 4.20 | Approve button works | ⬜ |
| 4.21 | Reject button works (requires reason) | ⬜ |
| 4.22 | User can create manual rule | ⬜ |

### Settings

| # | Criterion | Status |
|---|-----------|--------|
| 4.23 | All settings sections render | ⬜ |
| 4.24 | AI settings can be saved | ⬜ |
| 4.25 | Retention settings can be saved | ⬜ |
| 4.26 | Alert settings can be saved | ⬜ |
| 4.27 | Telegram link flow works | ⬜ |

### Reports

| # | Criterion | Status |
|---|-----------|--------|
| 4.28 | Report list loads | ⬜ |
| 4.29 | Generate report button triggers job | ⬜ |
| 4.30 | Report download via signed URL works | ⬜ |

### Audit Logs

| # | Criterion | Status |
|---|-----------|--------|
| 4.31 | Audit log list loads | ⬜ |
| 4.32 | Filters work (actor, action, date) | ⬜ |
| 4.33 | Detail view shows before/after diff | ⬜ |

**FAIL if:** Frontend reimplements ThingsBoard dashboards.

**Deliverable:** Usable operator console without rebuilding dashboards

---

## Final Sign-Off

| Phase | Status | Date | Verified By |
|-------|--------|------|-------------|
| Phase 0 | ⬜ | | |
| Phase 1 | ⬜ | | |
| Phase 2 | ⬜ | | |
| Phase 3 | ⬜ | | |
| Phase 4 | ⬜ | | |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | PASS |
| ❌ | FAIL |

---

## References

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [Operational Hardening](./OPERATIONAL_HARDENING.md)
- [Frontend Specification](./FRONTEND_SPEC.md)
- [API Contract](./API_CONTRACT.md)
