"""
AFASA 2.0 - Policy Gate
AI rule proposal governance
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func
import sys
sys.path.insert(0, '/app/services')

from common import (
    get_tenant_session, TenantSettings, RuleProposal, AuditLog
)


async def evaluate_proposal(
    tenant_id: str,
    proposal: Dict[str, Any],
    confidence: float
) -> Tuple[bool, str]:
    """
    Evaluate if an AI rule proposal can be auto-activated.
    Returns (can_auto_activate, reason).
    """
    async with get_tenant_session(tenant_id) as session:
        # Get tenant settings
        result = await session.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == UUID(tenant_id))
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            return False, "Tenant settings not found"
        
        # Check if AI rule creation is allowed
        if settings.ai_rule_creation == "suggest_only":
            return False, "Tenant policy requires manual approval"
        
        # Check if auto-activation is enabled
        if not settings.ai_auto_activation:
            return False, "Auto-activation disabled"
        
        # Check confidence threshold (minimum 0.8)
        if confidence < 0.8:
            return False, f"Confidence {confidence} below threshold 0.8"
        
        # Check daily change limit
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        changes_result = await session.execute(
            select(func.count(RuleProposal.id)).where(
                RuleProposal.tenant_id == UUID(tenant_id),
                RuleProposal.status == "activated",
                RuleProposal.approved_at >= today_start
            )
        )
        daily_changes = changes_result.scalar()
        
        if daily_changes >= settings.max_daily_rule_changes:
            return False, f"Daily change limit ({settings.max_daily_rule_changes}) reached"
        
        # Check protected devices
        proposed_device = proposal.get("action", {}).get("device_id")
        if proposed_device and proposed_device in settings.protected_devices:
            return False, f"Device {proposed_device} is protected"
        
        return True, "Approved for auto-activation"


async def create_proposal(
    tenant_id: str,
    intent_type: str,
    proposed_rule: Dict[str, Any],
    confidence: float,
    actor_id: str = "ai"
) -> RuleProposal:
    """
    Create a new rule proposal and evaluate it.
    """
    # Evaluate if can auto-activate
    can_auto, reason = await evaluate_proposal(tenant_id, proposed_rule, confidence)
    
    async with get_tenant_session(tenant_id) as session:
        proposal = RuleProposal(
            tenant_id=UUID(tenant_id),
            intent_type=intent_type,
            proposed_rule=proposed_rule,
            confidence=confidence,
            requires_approval=not can_auto,
            status="pending" if not can_auto else "approved",
            created_by=actor_id
        )
        session.add(proposal)
        
        # Create audit log
        audit = AuditLog(
            tenant_id=UUID(tenant_id),
            actor_type="ai" if actor_id == "ai" else "user",
            actor_id=actor_id,
            action="rule_proposed",
            target_type="rule_proposal",
            target_id=str(proposal.id) if proposal.id else "pending",
            reason=reason,
            confidence=confidence,
            after={"proposal": proposed_rule}
        )
        session.add(audit)
        
        await session.flush()
        await session.refresh(proposal)
        
        return proposal


async def approve_proposal(
    tenant_id: str,
    proposal_id: UUID,
    actor_id: str
) -> RuleProposal:
    """
    Manually approve a pending proposal.
    """
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(RuleProposal).where(RuleProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError("Proposal not found")
        
        if proposal.status != "pending":
            raise ValueError(f"Proposal already {proposal.status}")
        
        old_status = proposal.status
        proposal.status = "approved"
        proposal.approved_at = datetime.now(timezone.utc)
        
        # Create audit log
        audit = AuditLog(
            tenant_id=UUID(tenant_id),
            actor_type="user",
            actor_id=actor_id,
            action="rule_approved",
            target_type="rule_proposal",
            target_id=str(proposal_id),
            before={"status": old_status},
            after={"status": "approved"}
        )
        session.add(audit)
        
        await session.flush()
        await session.refresh(proposal)
        
        return proposal


async def reject_proposal(
    tenant_id: str,
    proposal_id: UUID,
    actor_id: str,
    reason: str = None
) -> RuleProposal:
    """
    Reject a pending proposal.
    """
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(RuleProposal).where(RuleProposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        
        if not proposal:
            raise ValueError("Proposal not found")
        
        old_status = proposal.status
        proposal.status = "rejected"
        
        # Create audit log
        audit = AuditLog(
            tenant_id=UUID(tenant_id),
            actor_type="user",
            actor_id=actor_id,
            action="rule_rejected",
            target_type="rule_proposal",
            target_id=str(proposal_id),
            reason=reason,
            before={"status": old_status},
            after={"status": "rejected"}
        )
        session.add(audit)
        
        await session.flush()
        await session.refresh(proposal)
        
        return proposal
