# AFASA 2.0 - AI Collaboration Brief
**For: ChatGPT Plus (Secondary AI)**  
**From: Antigravity (Primary AI)**  
**Date: 2026-01-26**

---

## 🎯 Project Overview
**AFASA 2.0** is a multi-tenant AI agricultural monitoring system built with microservices architecture. It combines:
- **Computer Vision** (YOLOv8 + Gemini AI) for crop/pest detection
- **IoT Integration** (ThingsBoard + UbiBot) for sensor data
- **Event-Driven Architecture** (NATS JetStream)
- **Multi-tenancy** with Row-Level Security (Postgres + Keycloak)

---

## 📁 Project Structure (Clean)
```
afasa2.0/
├── services/               # Microservices
│   ├── common/            # Shared library (models, auth, events)
│   ├── ops/               # Task & rule engine
│   ├── tb_adapter/        # ThingsBoard & UbiBot integration
│   ├── vision_yolo/       # Object detection
│   ├── vision_reasoner/   # AI analysis (Gemini)
│   ├── media/             # Snapshot & video management
│   ├── report/            # PDF/CSV generation
│   ├── telegram/          # Telegram bot
│   ├── portal/            # React frontend
│   └── retention_cleaner/ # Data cleanup
├── infra/                 # Infrastructure configs
├── docs/                  # Documentation
├── docker-compose.yml     # Full stack deployment
├── .env.example           # Environment template
├── README.md              # Main documentation
└── problem_statement.md   # Current issues (READ THIS FIRST)
```

**Archived** (old deployment notes): `archive/`

---

## 🚨 Current State & Problems

### What Works ✅
- **Architecture**: Event bus, database, auth are solid
- **Common Library**: Models, events, DB connections are complete
- **Infrastructure**: Docker Compose setup is production-ready

### What's Broken ❌
**Critical Issues** (from `problem_statement.md`):

1. **Device Sync Not Saving** (`tb_adapter`)
   - File: `services/tb_adapter/app/routes_extended.py`
   - Function: `sync_ubibot()` (line ~267)
   - Problem: Discovers devices but **doesn't save to DB** (commented stub)
   - Impact: No devices appear in system

2. **Device Controls Are Stubs** (`tb_adapter`)
   - File: `services/tb_adapter/app/routes_extended.py`
   - Functions: `enable_device()`, `disable_device()` (lines ~197, ~207)
   - Problem: Return `{"success": True}` without doing anything
   - Impact: Users can't control devices

3. **Report Generation Blocks API** (`report`)
   - File: `services/report/app/subscriber.py`
   - Problem: Reports are generated synchronously (will timeout)
   - Impact: Long reports crash the API

---

## 🎯 Your Mission (ChatGPT)

### Phase 1: Fix Critical Stubs
**Priority: HIGH**

#### Task 1.1: Implement Device Sync
**File**: `services/tb_adapter/app/routes_extended.py`  
**Function**: `sync_ubibot()` (around line 267)

**Current Code** (stub):
```python
for channel in channels:
    # Create device entry (simplified)
    # In real implementation, would check for existing and update
    created += 1
```

**What You Need to Do**:
1. For each UbiBot channel, create a `Camera` model instance (or generic device)
2. Check if device already exists (by external ID or name)
3. If exists: **update** metadata
4. If new: **insert** into database
5. Use `session.add()` and `await session.flush()`
6. Follow the pattern from `add_camera()` function above it

**Reference Models**: See `services/common/models.py` for `Camera` schema

---

#### Task 1.2: Implement Device Controls
**File**: `services/tb_adapter/app/routes_extended.py`  
**Functions**: `enable_device()`, `disable_device()`

**What You Need to Do**:
1. Query the device from DB by `device_id`
2. Add a `status` field to the device (or use existing field)
3. Update status to "enabled" or "disabled"
4. Optionally: Call ThingsBoard API to enable/disable on their side
5. Log the action using `audit.log()`

---

#### Task 1.3: Async Report Generation
**File**: `services/report/app/subscriber.py`

**What You Need to Do**:
1. Move report generation logic from API route to `handle_report_requested()`
2. The API should only:
   - Create a `Report` record with status="queued"
   - Publish `REPORT_REQUESTED` event
   - Return HTTP 202 (Accepted)
3. The subscriber should:
   - Generate the report (PDF/CSV)
   - Upload to MinIO
   - Update `Report.status = "ready"` and set `s3_key`
   - Publish `REPORT_READY` event

---

## 🛠️ Development Guidelines

### Code Style
- **Python**: Follow existing patterns in `services/common/`
- **Async/Await**: All DB operations use `async with get_tenant_session()`
- **Error Handling**: Wrap external API calls in try/except
- **Logging**: Use `print()` for now (will upgrade to structured logging later)

### Database Access
```python
from common import get_tenant_session, Camera
from uuid import UUID

async with get_tenant_session(token.tenant_id) as session:
    camera = Camera(
        tenant_id=UUID(token.tenant_id),
        name="Device Name",
        # ... other fields
    )
    session.add(camera)
    await session.flush()
    await session.refresh(camera)
```

### Event Publishing
```python
from common import get_event_bus, Subjects

event_bus = await get_event_bus()
await event_bus.publish(
    subject=Subjects.REPORT_REQUESTED,
    tenant_id=tenant_id,
    data={"report_id": str(report.id)},
    producer="report-api"
)
```

---

## 📋 Testing Checklist
After your changes:
1. [ ] Code compiles (no syntax errors)
2. [ ] Imports are correct
3. [ ] Database models match `services/common/models.py`
4. [ ] Functions follow async/await patterns
5. [ ] Error handling added for external APIs

---

## 🤝 Collaboration Protocol
1. **Read** `problem_statement.md` first
2. **Fix** one task at a time (don't refactor everything)
3. **Test** your changes mentally (does it match the pattern?)
4. **Comment** your code where logic is complex
5. **Ask** if you need clarification on architecture

---

## 📞 Questions for Antigravity?
If you're unsure about:
- Database schema details
- Event bus subjects
- External API formats (UbiBot, ThingsBoard)

**Leave a comment in your code** like:
```python
# TODO: Antigravity - Need to confirm UbiBot channel ID mapping
```

---

## 🚀 Ready to Start?
**Your first file to edit**: `services/tb_adapter/app/routes_extended.py`  
**Your first function**: `sync_ubibot()` (line ~267)

Good luck! 🤖🤝🤖
