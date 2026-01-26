# AFASA 2.0 - FRONTEND ROUTES + API CONTRACT TABLE

> **Document Status**: FROZEN
> **Last Updated**: 2026-01-21

---

## 1) Global Rules (Non-Negotiable)

1. **Frontend is a thin control-plane** - ThingsBoard = primary visualization layer
2. **Frontend embeds TB dashboards** via short-lived tokens
3. **Frontend NEVER**:
   - Connects to cameras
   - Stores credentials
   - Rebuilds dashboards
   - Embeds TB admin sessions
4. **All frontend API calls go through AFASA API Gateway**

---

## 2) Authentication & Tenant Context

### Flow
- Keycloak OIDC (Authorization Code + PKCE)
- JWT contains `tenant_id`
- Frontend **never** asks user to choose tenant

### Required Endpoint

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| `GET` | `/api/me` | Return tenant context | `{ tenant_id, user_id, roles, tenant_name, settings_summary }` |

---

## 3) Frontend Routes → API Contracts

### 3.1 Landing (`/`)
No API dependency. Redirects to `/dashboard` if authenticated.

---

### 3.2 Main Dashboard (`/dashboard`)

**UI Components:**
- ThingsBoard dashboard iframe
- Snapshot gallery (latest)
- Tasks (today)
- Pending rule approvals
- AI assessments summary

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `POST` | `/api/tb/embed-token` | Get TB iframe URL/token | `{ dashboard_id? }` | `{ url, token, expires_at }` |
| `GET` | `/api/snapshots` | List snapshots | `?range=24h&camera_id=&label=` | `{ items: [...], total }` |
| `GET` | `/api/tasks` | List tasks | `?status=open&limit=10` | `{ items: [...] }` |
| `GET` | `/api/rule-proposals` | List pending rules | `?status=pending` | `{ items: [...] }` |
| `GET` | `/api/assessments/latest` | Latest AI outputs | `?limit=5` | `{ items: [...] }` |

---

### 3.3 Devices (`/devices`)

**Tabs:** Cameras / NVR / IoT / ThingsBoard

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/api/devices` | List all devices | `?type=camera&type=nvr&type=iot` | `{ items: [...] }` |
| `POST` | `/api/devices/camera` | Add single camera | `{ name, rtsp_url, onvif_host?, credentials_secret_ref }` | `{ id, status }` |
| `POST` | `/api/devices/nvr` | Add NVR | `{ name, host, port, credentials_secret_ref }` | `{ id, channels: [...] }` |
| `GET` | `/api/devices/{id}` | Get device details | - | `{ device }` |
| `POST` | `/api/devices/{id}/enable` | Enable device | - | `{ success }` |
| `POST` | `/api/devices/{id}/disable` | Disable device | - | `{ success }` |
| `DELETE` | `/api/devices/{id}` | Remove device | - | `{ success }` |
| `POST` | `/api/integrations/ubibot/connect` | Store UbiBot key | `{ api_key }` | `{ secret_ref, status }` |
| `POST` | `/api/discovery/ubibot/sync` | Sync UbiBot devices | - | `{ devices_found, devices_created }` |
| `GET` | `/api/integrations/ubibot/status` | UbiBot sync status | - | `{ last_sync, device_count }` |
| `POST` | `/api/integrations/thingsboard/connect` | Store TB JWT | `{ base_url, jwt }` | `{ secret_ref, dashboards: [...] }` |
| `GET` | `/api/integrations/thingsboard/dashboards` | List TB dashboards | - | `{ dashboards: [...] }` |

---

### 3.4 Rules & Approvals (`/rules`)

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/api/rules` | List active rules | `?origin=ai&origin=user` | `{ items: [...] }` |
| `GET` | `/api/rules/{id}` | Get rule details | - | `{ rule }` |
| `POST` | `/api/rules` | Create user rule | `{ name, trigger, action, target_device_id }` | `{ id }` |
| `PUT` | `/api/rules/{id}` | Update rule | `{ ...changes }` | `{ success }` |
| `DELETE` | `/api/rules/{id}` | Delete rule | - | `{ success }` |
| `GET` | `/api/rule-proposals` | List proposals | `?status=pending` | `{ items: [...] }` |
| `GET` | `/api/rule-proposals/{id}` | Get proposal details | - | `{ proposal }` |
| `POST` | `/api/rule-proposals/{id}/approve` | Approve proposal | `{ reason? }` | `{ rule_id, tb_rulechain_id? }` |
| `POST` | `/api/rule-proposals/{id}/reject` | Reject proposal | `{ reason }` | `{ success }` |

---

### 3.5 Tasks (`/tasks`)

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/api/tasks` | List tasks | `?status=&severity=&device_id=&from=&to=` | `{ items: [...], total }` |
| `GET` | `/api/tasks/{id}` | Get task details | - | `{ task, evidence: [...] }` |
| `POST` | `/api/tasks/{id}/status` | Update status | `{ status: 'in_progress' \| 'done' }` | `{ success }` |
| `POST` | `/api/tasks/{id}/notes` | Add note | `{ content }` | `{ note_id }` |

---

### 3.6 Reports (`/reports`)

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `POST` | `/api/reports/generate` | Request report | `{ type: 'daily'\|'weekly'\|'monthly'\|'custom', format: 'pdf'\|'xlsx', from?, to? }` | `{ job_id }` |
| `GET` | `/api/reports` | List reports | `?status=ready&format=` | `{ items: [...] }` |
| `GET` | `/api/reports/{id}` | Get report metadata | - | `{ report }` |
| `GET` | `/api/assets/signed-url` | Get download URL | `?key=reports/{id}.pdf` | `{ url, expires_at }` |

---

### 3.7 Settings (`/settings`)

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/api/settings` | Get all settings | - | `{ ai, retention, alerts, integrations }` |
| `POST` | `/api/settings/ai` | Update AI settings | `{ task_frequency, reasoning_frequency, confidence_threshold, autopilot_policy }` | `{ success }` |
| `POST` | `/api/settings/retention` | Update retention | `{ snapshots_days, annotated_days, reports_days }` | `{ success }` |
| `POST` | `/api/settings/alerts` | Update alerts | `{ cooldown_minutes, quiet_hours_start, quiet_hours_end, max_daily_alerts }` | `{ success }` |
| `POST` | `/api/integrations/telegram/link` | Link Telegram | `{ chat_id? }` | `{ bot_start_url }` or `{ linked: true }` |
| `POST` | `/api/secrets/rotate` | Rotate secrets | `{ secret_ref }` | `{ new_secret_ref }` |

---

### 3.8 Audit Logs (`/audit`)

**APIs:**

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `GET` | `/api/audit` | List audit entries | `?actor_type=&action=&from=&to=&limit=&offset=` | `{ items: [...], total }` |
| `GET` | `/api/audit/{id}` | Get audit details | - | `{ entry, before?, after? }` |
| `GET` | `/api/audit/export` | Export to CSV | `?from=&to=` | CSV file stream |

---

## 4) Common Response Envelope

All API responses follow this structure:

### Success
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-21T15:42:24Z"
  }
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": { ... }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-01-21T15:42:24Z"
  }
}
```

---

## 5) Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT |
| `FORBIDDEN` | 403 | Valid JWT but insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request body |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## 6) Headers

### Request Headers
| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <jwt>` |
| `X-Request-ID` | No | Client-provided correlation ID |
| `Content-Type` | Yes* | `application/json` for POST/PUT |

### Response Headers
| Header | Description |
|--------|-------------|
| `X-Request-ID` | Correlation ID (echoed or generated) |
| `X-RateLimit-Remaining` | Requests remaining in window |
| `X-RateLimit-Reset` | Window reset timestamp |

---

## References

- [Frontend Specification](./FRONTEND_SPEC.md)
- [Master Architecture](./MASTER_ARCHITECTURE.md)
