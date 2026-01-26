# AFASA 2.0 - FRONTEND SPECIFICATION (Complete)

> **Document Status**: FROZEN
> **Last Updated**: 2026-01-21
> **Key Principle**: Thin control-plane UI. ThingsBoard = visualization layer.

---

## 1) Tech Stack (Fixed)

| Layer | Technology |
|-------|------------|
| Build tool | Vite |
| Framework | React |
| Data fetching | TanStack Query |
| Styling | Tailwind CSS |
| Routing | React Router |
| Auth | Keycloak (OIDC Authorization Code + PKCE) |

### Non-Negotiables
- Portal talks **ONLY** to AFASA API Gateway (FastAPI)
- Portal **NEVER**:
  - Connects to cameras directly
  - Stores credentials (uses secret_ref pattern)
  - Rebuilds ThingsBoard dashboards
  - Embeds TB admin sessions

---

## 2) Layout (Fixed)

### App Shell
```
┌─────────────────────────────────────────────────────┐
│  [Tenant Name]  [Health Indicators]  [Search] [👤]  │
├───────┬─────────────────────────────────────────────┤
│       │                                             │
│  📊   │          MAIN CONTENT AREA                  │
│  🎥   │          (Responsive Grid)                  │
│  ⚙️   │                                             │
│  📋   │                                             │
│  📁   │                                             │
│  🔧   │                                             │
│  📜   │                                             │
│       │                                             │
└───────┴─────────────────────────────────────────────┘
```

### Components
- **Top bar**: tenant name + health indicators + quick search + user menu
- **Left off-canvas sidebar**: hover/click; overlay, does not resize
- **Main content area**: responsive grid
- **Toast notifications**: for async actions

### Sidebar Routes
| Route | Icon | Label |
|-------|------|-------|
| `/dashboard` | 📊 | Main Dashboard |
| `/devices` | 🎥 | Devices |
| `/rules` | ⚙️ | Rules & Approvals |
| `/tasks` | 📋 | Tasks |
| `/reports` | 📁 | Reports |
| `/settings` | 🔧 | Settings |
| `/audit` | 📜 | Audit Logs |

---

## 3) Page Specifications

### 3.1 Main Dashboard (`/dashboard`)

**Section A — ThingsBoard Embed (Primary)**
- iframe embed to selected TB dashboard (per tenant)
- TB token is short-lived and minted by AFASA API

**Section B — Live Views (Optional / MVP-lite)**
- HLS tiles (RTSP→HLS happens server-side via MediaMTX)
- Show camera availability + last frame time
- No inference overlay on live (overlay is snapshot-based)

**Section C — Plant Health AI Panel**
- Latest assessments (severity, confidence, actions)
- "Evidence" links (snapshot IDs, timestamps)
- Quick actions:
  - "Request new snapshot"
  - "Run reasoning now"

**Section D — Snapshot Gallery**
- Filters: last 24h / 7d / by camera / by label
- Each card shows:
  - Timestamp
  - Camera/channel
  - YOLO labels/confidence
  - "View annotated" action
  - "Send to reasoning" action

**Section E — Tasks**
- Today's tasks list
- Status updates (open/in-progress/done)
- Priority + due date

**Section F — Pending Approvals**
- Rule proposals awaiting approval
- Approve/reject with reason
- Policy tags (AI-proposed, safe/unsafe)

---

### 3.2 Devices Page (`/devices`)

**Tabs:**
| Tab | Content |
|-----|---------|
| Cameras | Direct IP cameras |
| NVRs | Network Video Recorders |
| IoT | UbiBot sensors |
| ThingsBoard | TB connection status |

**Camera Add Wizard (MVP)**

*Mode 1: "I have NVR"*
- Input: NVR host, port, user, password (stored as `secret_ref`)
- List channels (if possible) or accept manual channel RTSP

*Mode 2: "Single camera"*
- Input: RTSP URL + optional ONVIF host
- Validate RTSP connect test (server-side)
- Save as "VideoSource" in device registry

**UbiBot Connect**
- Input: UbiBot API key (stored as `secret_ref`)
- Click "Sync" → populate device registry
- Show last sync time, status

**ThingsBoard Connect**
- Input: TB base URL + JWT (`secret_ref`)
- Validate + show tenant dashboards available

**Device Lifecycle Actions**
- Enable/disable
- Health view (last seen, last telemetry, last snapshot)

---

### 3.3 Rules & Approvals Page (`/rules`)

**Display:**
- List current rules (user vs AI origin)
- List pending proposals (AI or user)

**For each rule/proposal show:**
- Trigger condition
- Action
- Target device
- Safety classification
- Reason + confidence

**Behavior:**
- Approve/reject does NOT directly execute device command
- It creates TB rulechain OR AFASA policy-based action routed via TB Adapter

---

### 3.4 Tasks Page (`/tasks`)

**List View:**
- Task cards with status badge
- Filters: date range, severity, device, status

**Task Detail:**
- Evidence references (snapshots/telemetry summary/audit record)
- Status update actions

---

### 3.5 Reports Page (`/reports`)

**Generate Report:**
- Period: daily/weekly/monthly/custom
- Output: PDF/XLSX stored in MinIO

**Report List:**
- Portal lists reports
- Uses signed URL for secure download

---

### 3.6 Settings Page (`/settings`)

**AI Behavior**
| Setting | Type | Description |
|---------|------|-------------|
| task_frequency | string | How often to generate tasks |
| reasoning_frequency | string | How often to run AI reasoning |
| confidence_threshold | number | Min confidence for auto-action |
| autopilot_policy | enum | `suggest_only` / `auto_activate` |

**Retention**
| Setting | Type | Description |
|---------|------|-------------|
| snapshots_days | number | Days to keep raw snapshots |
| annotated_days | number | Days to keep annotated images |
| reports_days | number | Days to keep reports |

**Alerts**
| Setting | Type | Description |
|---------|------|-------------|
| cooldown_minutes | number | Min time between similar alerts |
| quiet_hours_start | string | HH:MM start of quiet period |
| quiet_hours_end | string | HH:MM end of quiet period |
| max_daily_alerts | number | Daily alert cap |

**Integrations**
| Setting | Type | Description |
|---------|------|-------------|
| telegram_chat_id | string | Linked Telegram chat |
| ubibot_api_key | secret_ref | UbiBot API key |
| tb_jwt | secret_ref | ThingsBoard JWT |

**Security**
- Rotate secrets (admin only)

---

### 3.7 Audit Logs Page (`/audit`)

**Display:**
- Filter by actor_type / action / date
- View before/after diffs

**Actions:**
- Export CSV (optional)

---

## 4) Authentication Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Portal  │────▶│ Keycloak │────▶│ API GW   │
│  (PKCE)  │     │  (OIDC)  │     │  (JWT)   │
└──────────┘     └──────────┘     └──────────┘
      │                                 │
      └──────────── tenant_id ──────────┘
```

1. User visits Portal
2. Redirected to Keycloak login
3. Keycloak returns JWT with `tenant_id` claim
4. Portal stores token (memory, not localStorage for security)
5. All API calls include `Authorization: Bearer <token>`
6. API Gateway validates and extracts tenant context

**Frontend NEVER asks user to choose tenant** - it's in the JWT.

---

## 5) Component Library

### Required UI Components

| Component | Purpose |
|-----------|---------|
| `<AppShell>` | Layout wrapper with sidebar |
| `<TBEmbed>` | ThingsBoard iframe container |
| `<SnapshotCard>` | Gallery item for snapshots |
| `<TaskCard>` | Task list item |
| `<ApprovalCard>` | Rule proposal item |
| `<DeviceCard>` | Device registry item |
| `<MetricBadge>` | Health/status indicator |
| `<ConfirmDialog>` | Approval confirmation modal |
| `<Toast>` | Notification toast |

### Design Tokens (Tailwind)

```css
:root {
  --primary: #10B981;      /* Emerald green */
  --primary-dark: #059669;
  --accent: #F59E0B;       /* Amber gold */
  --danger: #EF4444;       /* Red */
  --bg-dark: #111827;      /* Gray 900 */
  --bg-card: #1F2937;      /* Gray 800 */
  --text-primary: #F9FAFB; /* Gray 50 */
  --text-muted: #9CA3AF;   /* Gray 400 */
}
```

---

## 6) Build Order (Phase 4 Implementation)

1. Auth + App shell + `/api/me` tenant context
2. Main Dashboard (TB embed + snapshot gallery + tasks + approvals)
3. Devices (Camera/NVR add + UbiBot connect/sync + TB connect)
4. Rules & Approvals
5. Settings (retention, alerts, AI policy, integrations)
6. Reports
7. Audit Logs

---

## References

- [API Contract Table](./API_CONTRACT.md)
- [Master Architecture](./MASTER_ARCHITECTURE.md)
