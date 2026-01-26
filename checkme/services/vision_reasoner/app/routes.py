"""
AFASA 2.0 - Vision Reasoner Routes
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, TokenPayload, get_tenant_session,
    get_event_bus, Subjects, get_storage_client,
    Assessment
)
from app.reasoner import get_reasoner

router = APIRouter(tags=["vision-reasoner"])


class TelemetrySummary(BaseModel):
    soil_moisture_avg: Optional[float] = None
    temp_avg: Optional[float] = None
    humidity_avg: Optional[float] = None


class DetectionContext(BaseModel):
    label: str
    confidence: float


class AssessRequest(BaseModel):
    snapshot_id: UUID
    camera_id: UUID
    s3_key: str
    context: Optional[Dict[str, Any]] = None


class HypothesisItem(BaseModel):
    name: str
    confidence: float
    evidence: str


class ActionItem(BaseModel):
    action: str
    priority: int
    notes: Optional[str] = None


class AssessResponse(BaseModel):
    assessment_id: UUID
    snapshot_id: UUID
    severity: str
    hypotheses: List[HypothesisItem]
    recommended_actions: List[ActionItem]
    created_at: datetime


@router.post("/assess", response_model=AssessResponse)
async def assess_snapshot(
    body: AssessRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Run Gemini reasoning on a snapshot"""
    storage = get_storage_client()
    reasoner = get_reasoner()
    
    # Get snapshot image from S3
    try:
        image_data = storage.get_object(body.s3_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get snapshot: {e}")
    
    # Build context
    context = body.context or {}
    if "crop" not in context:
        context["crop"] = "chili"
    if "farm_location" not in context:
        context["farm_location"] = "Malaysia"
    
    # Run reasoning
    result = await reasoner.assess(image_data, context)
    
    async with get_tenant_session(token.tenant_id) as session:
        # Store assessment
        assessment = Assessment(
            tenant_id=UUID(token.tenant_id),
            snapshot_id=body.snapshot_id,
            camera_id=body.camera_id,
            severity=result.get("severity", "low"),
            hypotheses=result.get("hypotheses", []),
            recommended_actions=result.get("recommended_actions", [])
        )
        session.add(assessment)
        await session.flush()
        await session.refresh(assessment)
        
        # Publish event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.ASSESSMENT_CREATED,
            token.tenant_id,
            {
                "assessment_id": str(assessment.id),
                "snapshot_id": str(body.snapshot_id),
                "camera_id": str(body.camera_id),
                "severity": result.get("severity", "low"),
                "hypotheses": result.get("hypotheses", []),
                "recommended_actions": result.get("recommended_actions", [])
            },
            producer="afasa-vision-reasoner"
        )
        
        return AssessResponse(
            assessment_id=assessment.id,
            snapshot_id=body.snapshot_id,
            severity=result.get("severity", "low"),
            hypotheses=[HypothesisItem(**h) for h in result.get("hypotheses", [])],
            recommended_actions=[ActionItem(**a) for a in result.get("recommended_actions", [])],
            created_at=assessment.created_at
        )
