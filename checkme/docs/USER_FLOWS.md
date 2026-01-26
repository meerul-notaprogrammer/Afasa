# AFASA 2.0 - USER FLOW ASSUMPTIONS

> **Document Status**: FROZEN
> **Last Updated**: 2026-01-21

---

## 1) Onboarding Flow (Tenant + Admin)

### Sequence Diagram
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Provisioning│  │  Keycloak   │  │  ThingsBoard│  │  Database   │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       │ 1. Create tenant                │                │
       │────────────────────────────────────────────────▶│
       │                │                │                │
       │ 2. Create default settings      │                │
       │────────────────────────────────────────────────▶│
       │                │                │                │
       │ 3. Create admin user            │                │
       │───────────────▶│                │                │
       │        (with tenant_id attr)    │                │
       │                │                │                │
       │ 4. (Optional) Create TB tenant  │                │
       │────────────────────────────────▶│                │
       │                │                │                │
```

### Steps

1. **Provisioning service creates:**
   - Tenant record in Postgres
   - Default tenant settings
   - Keycloak admin user with `tenant_id` attribute
   - (Optional) ThingsBoard tenant

2. **Admin logs in:**
   - Keycloak authentication (OIDC + PKCE)
   - JWT returned with `tenant_id` claim

3. **Portal shows Setup Checklist:**
   - [ ] Connect ThingsBoard
   - [ ] Connect Telegram
   - [ ] Add NVR/cameras
   - [ ] Connect UbiBot and sync

4. **Setup completes when:**
   - At least 1 VideoSource exists
   - Telemetry ingestion active OR TB embedded dashboard set

---

## 2) Daily Operation Flow

### Sequence Diagram
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Scheduler │  │  Media   │  │  YOLO    │  │ Reasoner │  │   Ops    │  │ Telegram │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │             │
     │ 1. Trigger  │             │             │             │             │
     │────────────▶│             │             │             │             │
     │             │             │             │             │             │
     │             │ 2. Capture snapshot       │             │             │
     │             │─────────────────────────▶ (MinIO)       │             │
     │             │             │             │             │             │
     │             │ 3. Publish event          │             │             │
     │             │────────────▶│             │             │             │
     │             │             │             │             │             │
     │             │             │ 4. Run YOLO │             │             │
     │             │             │─────────────────────────▶ (MinIO)       │
     │             │             │             │             │             │
     │             │             │ 5. Publish event          │             │
     │             │             │────────────▶│             │             │
     │             │             │             │             │             │
     │             │             │             │ 6. Run reasoning          │
     │             │             │             │─────────────────────────▶ (AI)
     │             │             │             │             │             │
     │             │             │             │ 7. Create tasks           │
     │             │             │             │────────────▶│             │
     │             │             │             │             │             │
     │             │             │             │             │ 8. Send summary
     │             │             │             │             │────────────▶│
     │             │             │             │             │             │
```

### Steps

1. **Scheduler triggers snapshot collection** (interval policy)
2. **Media service captures snapshot** from RTSP stream
3. **YOLO processes snapshots** (confidence, bboxes, labels)
4. **Reasoner runs on selected snapshots** (AI policy)
5. **Tasks generated** based on assessments
6. **Telegram sends summary** (rate-limited)

### Portal Shows
- New tasks
- New assessments
- Pending approvals

---

## 3) Rule Proposal/Approval Flow

### Sequence Diagram
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Reasoner │  │   Ops    │  │  Portal  │  │TB Adapter│  │  Audit   │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │             │
     │ 1. Propose rule           │             │             │
     │────────────▶│             │             │             │
     │             │             │             │             │
     │             │ 2. Store pending          │             │
     │             │───────────────────────────────────────▶ DB
     │             │             │             │             │
     │             │             │ 3. Show pending           │
     │             │◀────────────│             │             │
     │             │             │             │             │
     │             │             │ 4. Admin approves/rejects │
     │             │◀────────────│             │             │
     │             │             │             │             │
     │             │ 5. If approved            │             │
     │             │────────────────────────▶ │             │
     │             │      Create rulechain     │             │
     │             │             │             │             │
     │             │ 6. Log action             │             │
     │             │───────────────────────────────────────▶│
```

### States

| State | Description |
|-------|-------------|
| `pending` | AI proposed, awaiting human review |
| `approved` | Human approved, rulechain created |
| `rejected` | Human rejected with reason |
| `active` | Rule is currently executing |
| `disabled` | Rule manually disabled |

### Approval Creates
- TB rulechain activation
- OR AFASA policy-based action

### Audit Log Entry
```json
{
  "action": "rule.approved",
  "actor_type": "user",
  "actor_id": "admin@farm.local",
  "resource_type": "rule_proposal",
  "resource_id": "uuid",
  "before_state": { "status": "pending" },
  "after_state": { "status": "approved", "tb_rulechain_id": "..." },
  "reason": "Looks reasonable for irrigation control"
}
```

---

## 4) Incident Flow (Camera Offline)

### Sequence Diagram
```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Media   │  │   Ops    │  │ Telegram │  │  Audit   │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     │ 1. Health check fails     │             │
     │────────────▶│             │             │
     │             │             │             │
     │             │ 2. Check rate limit        │
     │             │───────▶ (Redis)           │
     │             │             │             │
     │             │ 3. If allowed, send alert │
     │             │────────────▶│             │
     │             │             │             │
     │             │ 4. Log alert sent/skipped │
     │             │───────────────────────────▶│
```

### Behavior

1. **Device health becomes "offline"**
2. **Portal banner shows** camera offline status
3. **Telegram alerts only once** per cooldown window
4. **Audit log entry** for offline alert

### Rate Limiting Rules
- Only one alert per device per cooldown period
- No alerts during quiet hours
- Daily alert cap per tenant

---

## 5) Snapshot → Assessment Flow

### Trigger Conditions

| Trigger | Description |
|---------|-------------|
| Interval | Every X minutes (configurable) |
| Motion | Motion detected by MediaMTX |
| Manual | User clicks "Request new snapshot" |

### Process

```
[RTSP Stream]
      │
      ▼ (interval/motion/manual)
[Snapshot Capture]
      │
      ▼
[Store in MinIO: tenant/{id}/snapshots/raw/...]
      │
      ▼
[Publish: afasa.media.v1.snapshot.captured]
      │
      ▼
[YOLO Inference]
      │
      ├── Labels: ["tomato_plant", "leaf_spot"]
      ├── Confidence: [0.92, 0.78]
      └── Bounding boxes: [...]
      │
      ▼
[Store annotated (optional)]
      │
      ▼
[Publish: afasa.vision.v1.yolo.completed]
      │
      ▼
[Reasoner (if policy allows)]
      │
      ├── Severity: "medium"
      ├── Confidence: 0.85
      └── Actions: ["Apply fungicide", "Increase ventilation"]
      │
      ▼
[Create Task]
      │
      ▼
[Publish: afasa.vision.v1.assessment.created]
      │
      ▼
[Telegram Summary (rate-limited)]
```

---

## 6) Report Generation Flow

### Trigger
- Manual: User clicks "Generate Report" in portal
- Scheduled: Daily/weekly cron job

### Process

```
[User Request / Scheduler]
      │
      ▼
[POST /api/reports/generate]
      │
      ├── type: "weekly"
      ├── format: "pdf"
      └── date_range: "2026-01-14 to 2026-01-21"
      │
      ▼
[Create job in queue]
      │
      ▼
[Report Service picks up job]
      │
      ├── Query assessments
      ├── Query tasks
      ├── Query telemetry
      └── Generate PDF/XLSX
      │
      ▼
[Upload to MinIO: tenant/{id}/reports/{date}/{uuid}.pdf]
      │
      ▼
[Update report record: status=ready]
      │
      ▼
[Publish: afasa.report.v1.ready]
      │
      ▼
[Telegram notification (optional)]
```

### Download
- User lists reports in portal
- Clicks download → API returns signed URL
- Signed URL expires after short period

---

## 7) Device Lifecycle Flow

### Add Device

```
[User in Portal]
      │
      ▼
[POST /api/devices/camera]
      │
      ├── name: "Greenhouse Cam 1"
      ├── rtsp_url: "rtsp://192.168.1.100:554/stream"
      └── credentials: { user: "...", pass: "..." }
      │
      ▼
[Store credentials as secret_ref]
      │
      ▼
[Validate RTSP connection (server-side)]
      │
      ├── Success: Create VideoSource record
      └── Failure: Return error, no record created
      │
      ▼
[Sync to ThingsBoard (if connected)]
      │
      ▼
[Audit log: device.added]
```

### Remove Device

```
[User in Portal]
      │
      ▼
[DELETE /api/devices/{id}]
      │
      ▼
[Check if device is protected]
      │
      ├── If protected: Return 403
      └── If not: Continue
      │
      ▼
[Soft delete or hard delete (by policy)]
      │
      ▼
[Remove from ThingsBoard (if synced)]
      │
      ▼
[Audit log: device.removed]
```

---

## References

- [Master Architecture](./MASTER_ARCHITECTURE.md)
- [Frontend Specification](./FRONTEND_SPEC.md)
- [API Contract](./API_CONTRACT.md)
