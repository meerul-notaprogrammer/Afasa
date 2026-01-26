# AFASA 2.0 System Audit & Problem Statement

## 1. System Audit

### Overview
AFASA 2.0 is a microservices-based architecture designed for agricultural monitoring, utilizing a unified event bus (NATS), shared persistence (Postgres, MinIO), and centralized identity (Keycloak).

### Services Inventory

| Service | Directory | Port (Internal) | Public Route | Purpose | Dependencies |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **afasa-common** | `services/common` | N/A | N/A | Shared library for models, events, DB, and auth. | None |
| **afasa-ops** | `services/ops` | 8000 | `/api/ops`, `/api/tasks` | Governance, rule engine, scheduling. | Postgres, NATS, Redis |
| **afasa-tb-adapter** | `services/tb_adapter` | 8000 | `/api/tb`, `/api/devices` | Integration with ThingsBoard & UbiBot. | Postgres, NATS, ThingsBoard |
| **afasa-vision-yolo** | `services/vision_yolo` | 8000 | `/api/vision/yolo` | Object detection (YOLOv8). | NATS, MinIO, Redis |
| **afasa-vision-reasoner** | `services/vision_reasoner` | 8000 | `/api/vision/reasoner` | AI Analysis using Gemini. | NATS, MinIO, Gemini API |
| **afasa-media** | `services/media` | 8000 | `/api/media` | Media management (Snapshots, Video). | Postgres, NATS, MinIO, MediaMTX |
| **afasa-report** | `services/report` | 8000 | `/api/report` | PDF/CSV Report Generation. | Postgres, NATS, MinIO |
| **afasa-telegram** | `services/telegram` | 8000 | `/api/telegram` | Telegram Bot Notifications. | Postgres, NATS, Redis |
| **afasa-portal** | `services/portal` | 5173 | `/portal` | Frontend Dashboard (React/Vite). | Keycloak, APIs |

### Infrastructure Compatibility
*   **Database**: Postgres 16 with Row Level Security (RLS) enabled.
*   **Event Bus**: NATS JetStream for persistent messaging.
*   **Storage**: MinIO (S3 compatible) for images/reports.
*   **Auth**: Keycloak 25.0 (OIDC).
*   **Gateway**: Traefik (Edge routing).

---

## 2. Problem Statement

While the architecture is sound and the foundation (`common` library) is robust, several critical service implementations contain incomplete logic ("stubs") that currently prevent full system functionality.

### Critical Issues Detected:
1.  **Incomplete Device Synchronization (`tb_adapter`)**
    *   File: `services/tb_adapter/app/routes_extended.py`
    *   Issue: The `sync_ubibot` function iterates through channels but contains a comment `# Create device entry (simplified)` and does **not** actually save devices to the database.
    *   Impact: Devices discovered from UbiBot will not appear in the system registry.

2.  **Stubbed Device Control (`tb_adapter`)**
    *   File: `services/tb_adapter/app/routes_extended.py`
    *   Issue: `enable_device` and `disable_device` endpoints return `{"success": True}` without performing any action.
    *   Impact: Users cannot control devices.

3.  **Synchronous Reporting Bottleneck (`report`)**
    *   File: `services/report/app/subscriber.py`
    *   Issue: The subscriber logs requests but comments state report generation is handled synchronously in the API.
    *   Impact: Long-running reports will timeout the API request. This should be asynchronous via the event bus.

4.  **Ops Policy Gate Verification (`ops`)**
    *   File: `services/ops/app/policy_gate.py` (Inferred)
    *   Issue: Needs verification that rules are correctly evaluated against incoming events.

---

## 3. Repair & Improvement Plan

This plan phases the fixes from critical logical gaps to architectural improvements.

### Phase 1: Critical Logic Implementation (Fixing Stubs)
**Objective**: Ensure data properly flows from integrations to the database.
*   **Task 1.1**: Implement actual DB insertion/upsert logic in `sync_ubibot` (`services/tb_adapter/app/routes_extended.py`).
*   **Task 1.2**: Implement real logic for `enable_device`/`disable_device` (updating DB status and potentially notifying external APIs).
*   **Task 1.3**: Validate `Camera` model creation matches the `models.py` schema (e.g., handling ONVIF credentials).

### Phase 2: Asynchronous Workflow Implementation
**Objective**: Move long-running tasks to background workers.
*   **Task 2.1**: Refactor `afasa-report` to generate reports proactively upon receiving `REPORT_REQUESTED` events.
*   **Task 2.2**: Update the API to simply publish the event and return a "Job Started" status (HTTP 202).

### Phase 3: Policy & Rule Engine Verification
**Objective**: Ensure the "brain" of the system works.
*   **Task 3.1**: Create test events (mock NATS messages) to verify `afasa-ops` correctly triggers tasks or alerts based on rules.
*   **Task 3.2**: Verify `afasa-vision-reasoner` correctly consumes `SNAPSHOT_CREATED` events and publishes `ASSESSMENT_CREATED`.

### Phase 4: Operational Hardening
**Objective**: Production readiness.
*   **Task 4.1**: Add proper error handling (try/except) around all external API calls (UbiBot, ThingsBoard, Gemini).
*   **Task 4.2**: Ensure all Environment Variables are documented and validated on startup.
