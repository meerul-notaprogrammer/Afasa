"""
AFASA 2.0 - Vision YOLO Routes
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, TokenPayload, get_tenant_session,
    get_event_bus, Subjects, get_storage_client,
    Detection, Snapshot
)
from app.infer import get_detector
from app.cooldown import check_cooldown, update_cooldown

router = APIRouter(tags=["vision-yolo"])


class InferRequest(BaseModel):
    snapshot_id: UUID
    camera_id: UUID
    s3_key: str
    model: str = "yolov8n"
    threshold: float = 0.5


class DetectionItem(BaseModel):
    label: str
    confidence: float
    bbox: List[float]


class InferResponse(BaseModel):
    detection_batch_id: UUID
    snapshot_id: UUID
    detections: List[DetectionItem]
    annotated_s3_key: Optional[str]
    created_at: datetime


class CooldownCheckRequest(BaseModel):
    camera_id: UUID
    label: str
    confidence: float


class CooldownCheckResponse(BaseModel):
    should_alert: bool
    cooldown_remaining_sec: int


@router.post("/infer/snapshot", response_model=InferResponse)
async def infer_snapshot(
    body: InferRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Run YOLO inference on a snapshot"""
    storage = get_storage_client()
    detector = get_detector()
    
    # Get snapshot image from S3
    try:
        image_data = storage.get_object(body.s3_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get snapshot: {e}")
    
    # Run inference
    result = detector.infer(image_data, threshold=body.threshold)
    
    async with get_tenant_session(token.tenant_id) as session:
        # Upload annotated image if we have detections
        annotated_s3_key = None
        if result["annotated_data"]:
            annotated_s3_key = storage.upload_annotated(
                token.tenant_id,
                str(body.snapshot_id),
                result["annotated_data"]
            )
        
        # Store detections
        detection_ids = []
        for det in result["detections"]:
            detection = Detection(
                tenant_id=UUID(token.tenant_id),
                snapshot_id=body.snapshot_id,
                camera_id=body.camera_id,
                label=det["label"],
                confidence=det["confidence"],
                bbox=det["bbox"],
                model=body.model,
                annotated_s3_key=annotated_s3_key
            )
            session.add(detection)
            await session.flush()
            detection_ids.append(detection.id)
        
        # Publish event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.DETECTION_CREATED,
            token.tenant_id,
            {
                "detection_batch_id": str(detection_ids[0]) if detection_ids else str(body.snapshot_id),
                "snapshot_id": str(body.snapshot_id),
                "camera_id": str(body.camera_id),
                "model": body.model,
                "threshold": body.threshold,
                "detections": result["detections"],
                "annotated_s3_key": annotated_s3_key
            },
            producer="afasa-vision-yolo"
        )
        
        return InferResponse(
            detection_batch_id=detection_ids[0] if detection_ids else body.snapshot_id,
            snapshot_id=body.snapshot_id,
            detections=[DetectionItem(**d) for d in result["detections"]],
            annotated_s3_key=annotated_s3_key,
            created_at=datetime.now(timezone.utc)
        )


@router.post("/policy/cooldown/check", response_model=CooldownCheckResponse)
async def cooldown_check(
    body: CooldownCheckRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Check if detection should trigger alert (cooldown policy)"""
    should_alert, remaining = await check_cooldown(
        token.tenant_id,
        str(body.camera_id),
        body.label,
        body.confidence
    )
    
    if should_alert:
        await update_cooldown(token.tenant_id, str(body.camera_id), body.label)
    
    return CooldownCheckResponse(
        should_alert=should_alert,
        cooldown_remaining_sec=remaining
    )
