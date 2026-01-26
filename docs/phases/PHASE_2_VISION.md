# Phase 2: Vision Core (Production MVP)

> **Status**: CORE FUNCTIONALITY
> **Prerequisite**: Phase 1 complete (hardening done)
> **Duration**: 2-3 weeks

---

## Objective

Build the end-to-end AI monitoring pipeline: RTSP capture → YOLO inference → AI reasoning → task generation → notifications.

---

## Overview

```
[RTSP Stream] → [Snapshot] → [YOLO] → [Reasoner] → [Tasks] → [Telegram]
```

---

## 1) RTSP Snapshot Capture (afasa-media)

### Requirements
- Capture frames from RTSP streams at configured intervals
- Support motion-triggered captures (via MediaMTX)
- Store snapshots in MinIO with tenant prefix

### Implementation Tasks

1. **Snapshot Engine**
   ```python
   async def capture_snapshot(video_source: VideoSource) -> Snapshot:
       # 1. Get RTSP URL (decrypt secret_ref)
       # 2. Connect via OpenCV or ffmpeg
       # 3. Capture single frame
       # 4. Upload to MinIO: tenant/{id}/snapshots/raw/{date}/{uuid}.jpg
       # 5. Create database record
       # 6. Publish event
   ```

2. **Scheduler Integration**
   - Use APScheduler or similar
   - Configurable interval per video source

3. **Event Publishing**
   ```python
   await nats.publish(
       "afasa.media.v1.snapshot.captured",
       {
           "tenant_id": str(tenant_id),
           "snapshot_id": str(snapshot.id),
           "video_source_id": str(video_source.id),
           "minio_key": snapshot.minio_key,
           "timestamp": utc_now().isoformat()
       }
   )
   ```

### Verification
- [ ] RTSP snapshot capture works
- [ ] Snapshots stored in MinIO with tenant prefix
- [ ] Event published: `afasa.media.v1.snapshot.captured`

---

## 2) YOLO Inference (afasa-vision-yolo)

### Requirements
- Process snapshots (not live streams)
- Return labels, confidence, bounding boxes
- Optional: generate annotated images

### Implementation Tasks

1. **YOLO Service**
   ```python
   class YOLOService:
       def __init__(self):
           self.model = YOLO("yolov8n.pt")  # Or custom model
       
       async def process(self, image_bytes: bytes) -> YOLOResult:
           results = self.model(image_bytes)
           return YOLOResult(
               labels=[r.name for r in results],
               confidences=[r.confidence for r in results],
               bboxes=[r.bbox for r in results]
           )
   ```

2. **Event Subscriber**
   ```python
   @nats.subscribe("afasa.media.v1.snapshot.captured")
   async def on_snapshot(event):
       # 1. Download from MinIO
       # 2. Run YOLO
       # 3. Store results in database
       # 4. (Optional) Generate annotated image
       # 5. Publish completion event
   ```

3. **Annotated Image Generation**
   ```python
   async def create_annotated(image: bytes, results: YOLOResult) -> bytes:
       # Draw bounding boxes and labels
       # Upload to MinIO: tenant/{id}/snapshots/annotated/{date}/{uuid}.jpg
   ```

### Verification
- [ ] YOLO inference runs on snapshots
- [ ] Confidence + bounding box returned
- [ ] Annotated images generated (configurable)
- [ ] Event published: `afasa.vision.v1.yolo.completed`

---

## 3) AI Reasoning (afasa-vision-reasoner)

### Requirements
- Analyze YOLO results with AI context
- Generate severity assessment
- Propose actions

### Implementation Tasks

1. **Reasoner Service**
   ```python
   class ReasonerService:
       async def analyze(
           self,
           snapshot: Snapshot,
           yolo_result: YOLOResult,
           tenant_settings: TenantSettings
       ) -> Assessment:
           prompt = self.build_prompt(snapshot, yolo_result)
           response = await self.ai_client.generate(prompt)
           return Assessment(
               severity=response.severity,
               confidence=response.confidence,
               observations=response.observations,
               actions=response.recommended_actions,
               reason=response.reasoning
           )
   ```

2. **AI Integration**
   - Support Gemini (primary)
   - Fallback to OpenAI if needed
   - API keys via secret_ref

3. **Policy Check**
   ```python
   # Only run reasoning if policy allows
   if tenant_settings.autopilot_policy == "suggest_only":
       assessment.requires_approval = True
   ```

### Verification
- [ ] Reasoner runs on curated snapshots
- [ ] Assessment includes severity, confidence, actions
- [ ] Event published: `afasa.vision.v1.assessment.created`

---

## 4) Task Generation (afasa-ops)

### Requirements
- Create tasks from assessments
- Track status (open/in-progress/done)
- Link to evidence (snapshots, assessments)

### Implementation Tasks

1. **Task Service**
   ```python
   async def create_task_from_assessment(assessment: Assessment):
       task = Task(
           tenant_id=assessment.tenant_id,
           title=f"Action Required: {assessment.severity}",
           description=assessment.observations,
           priority=severity_to_priority(assessment.severity),
           due_date=calculate_due_date(assessment.severity),
           evidence=[{
               "type": "assessment",
               "id": str(assessment.id)
           }]
       )
       await db.save(task)
       await nats.publish("afasa.ops.v1.task.created", task.to_event())
   ```

2. **Event Subscriber**
   ```python
   @nats.subscribe("afasa.vision.v1.assessment.created")
   async def on_assessment(event):
       # Create task based on severity
       # Audit log entry
   ```

### Verification
- [ ] Tasks generated from assessments
- [ ] Event published: `afasa.ops.v1.task.created`

---

## 5) Telegram Notifications (afasa-telegram)

### Requirements
- Send summary notifications
- Respect rate limits and quiet hours
- Link to portal for details

### Implementation Tasks

1. **Notification Service**
   ```python
   async def send_task_notification(task: Task):
       # 1. Check rate limits
       allowed, skip_reason = await rate_limiter.should_send(
           tenant_id=task.tenant_id,
           alert_type="task"
       )
       
       if not allowed:
           await audit.log(action="alert.skipped", reason=skip_reason)
           return
       
       # 2. Format message
       message = format_task_message(task)
       
       # 3. Send via Telegram API
       await telegram.send_message(chat_id, message)
       
       # 4. Record sent
       await rate_limiter.record_sent(task.tenant_id, "task")
       await audit.log(action="alert.sent")
   ```

2. **Message Formatting**
   ```python
   def format_task_message(task: Task) -> str:
       return f"""
   🌱 *New Task Created*
   
   *Priority:* {task.priority}
   *Due:* {task.due_date}
   
   {task.description}
   
   [View in Portal]({portal_url}/tasks/{task.id})
   """
   ```

### Verification
- [ ] Telegram summary notifications sent
- [ ] Rate limiting enforced
- [ ] Quiet hours respected

---

## Event Flow Summary

```
┌──────────┐
│ Scheduler│
└────┬─────┘
     │ trigger
     ▼
┌──────────┐     afasa.media.v1.snapshot.captured
│  Media   │────────────────────────────────────────▶
└──────────┘                                         │
                                                     ▼
                                              ┌──────────┐
                                              │   YOLO   │
                                              └────┬─────┘
                                                   │
     afasa.vision.v1.yolo.completed                ▼
◀──────────────────────────────────────────────────┤
│                                                   │
▼                                                   ▼
┌──────────┐     afasa.vision.v1.assessment.created
│ Reasoner │────────────────────────────────────────▶
└──────────┘                                         │
                                                     ▼
                                              ┌──────────┐
                                              │   Ops    │
                                              └────┬─────┘
                                                   │
     afasa.ops.v1.task.created                     ▼
◀──────────────────────────────────────────────────┤
│                                                   │
▼                                                   ▼
┌──────────┐
│ Telegram │
└──────────┘
```

---

## Deliverables

1. Working snapshot capture from RTSP
2. YOLO inference on snapshots
3. AI reasoning generating assessments
4. Tasks created from assessments
5. Telegram notifications with rate limiting

---

## FAIL Condition

**FAIL if:** YOLO runs on full live stream (must be snapshot-only).

---

## References

- [Master Architecture](../MASTER_ARCHITECTURE.md)
- [MVP Acceptance Checklist](../MVP_ACCEPTANCE_CHECKLIST.md) - Phase 2 criteria
