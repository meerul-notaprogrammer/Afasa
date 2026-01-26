"""
AFASA 2.0 - Ops Service Routes
"""
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, require_role, TokenPayload, get_tenant_session,
    get_event_bus, Subjects, Task, RuleProposal
)
from app.scheduler import run_job_now
from app.policy_gate import create_proposal, approve_proposal, reject_proposal

router = APIRouter(tags=["ops"])


# Request/Response Models
class ScheduleCreate(BaseModel):
    name: str
    type: str = "cron"
    cron: str
    enabled: bool = True
    job: str


class ScheduleResponse(BaseModel):
    id: str
    name: str
    type: str
    cron: str
    enabled: bool
    job: str


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    priority: int
    status: str
    source: str
    due_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class RuleProposalCreate(BaseModel):
    intent_type: str
    proposed_rule: Dict[str, Any]
    confidence: float
    requires_approval: bool = True


class RuleProposalResponse(BaseModel):
    id: UUID
    intent_type: str
    proposed_rule: Dict[str, Any]
    confidence: float
    requires_approval: bool
    status: str
    tb_rule_id: Optional[str]
    created_by: str
    created_at: datetime
    approved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: str,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Manually trigger a scheduled job"""
    ok = await run_job_now(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {"run_id": str(UUID(int=0)), "ok": True}


@router.get("/tasks/today", response_model=List[TaskResponse])
async def get_today_tasks(token: TokenPayload = Depends(verify_token)):
    """Get tasks for today"""
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_end = datetime.combine(date.today(), datetime.max.time()).replace(tzinfo=timezone.utc)
    
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Task).where(
                Task.status == "open"
            ).order_by(Task.priority.asc())
        )
        tasks = result.scalars().all()
        return tasks


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    token: TokenPayload = Depends(verify_token)
):
    """List all tasks"""
    async with get_tenant_session(token.tenant_id) as session:
        query = select(Task)
        if status:
            query = query.where(Task.status == status)
        query = query.order_by(Task.created_at.desc())
        
        result = await session.execute(query)
        tasks = result.scalars().all()
        return tasks


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Mark a task as complete"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.status = "done"
        await session.flush()
        
        return {"ok": True}


@router.post("/rules/proposals", response_model=RuleProposalResponse)
async def create_rule_proposal(
    body: RuleProposalCreate,
    token: TokenPayload = Depends(verify_token)
):
    """Create a new rule proposal"""
    proposal = await create_proposal(
        token.tenant_id,
        body.intent_type,
        body.proposed_rule,
        body.confidence,
        actor_id=token.sub
    )
    
    # Publish event
    event_bus = await get_event_bus()
    await event_bus.publish(
        Subjects.RULE_PROPOSED,
        token.tenant_id,
        {
            "proposal_id": str(proposal.id),
            "intent_type": body.intent_type,
            "proposed_rule": body.proposed_rule,
            "confidence": body.confidence,
            "requires_approval": proposal.requires_approval
        },
        producer="afasa-ops"
    )
    
    return proposal


@router.get("/rules/proposals", response_model=List[RuleProposalResponse])
async def list_proposals(
    status: Optional[str] = None,
    token: TokenPayload = Depends(verify_token)
):
    """List rule proposals"""
    async with get_tenant_session(token.tenant_id) as session:
        query = select(RuleProposal)
        if status:
            query = query.where(RuleProposal.status == status)
        query = query.order_by(RuleProposal.created_at.desc())
        
        result = await session.execute(query)
        proposals = result.scalars().all()
        return proposals


@router.post("/rules/proposals/{proposal_id}/approve", response_model=RuleProposalResponse)
async def approve_rule_proposal(
    proposal_id: UUID,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Approve a pending rule proposal"""
    try:
        proposal = await approve_proposal(token.tenant_id, proposal_id, token.sub)
        
        # Publish event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.RULE_ACTIVATED,
            token.tenant_id,
            {
                "proposal_id": str(proposal.id),
                "tb_rule_id": proposal.tb_rule_id,
                "activated_by": "user",
                "activated_at": proposal.approved_at.isoformat() if proposal.approved_at else None
            },
            producer="afasa-ops"
        )
        
        return proposal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rules/proposals/{proposal_id}/reject")
async def reject_rule_proposal(
    proposal_id: UUID,
    reason: Optional[str] = None,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Reject a pending rule proposal"""
    try:
        proposal = await reject_proposal(token.tenant_id, proposal_id, token.sub, reason)
        return {"ok": True, "status": proposal.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
