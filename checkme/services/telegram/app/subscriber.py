"""
AFASA 2.0 - Telegram Notification Subscriber
Listens for outbound notification events
"""
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus, EventEnvelope, Subjects, TelegramLink
from common.db import AsyncSessionLocal
from app.send import get_sender


async def handle_telegram_outbound(envelope: EventEnvelope):
    """Handle outbound notification events"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    chat_id = data.get("chat_id")
    message = data.get("message")
    level = data.get("level", "info")
    link = data.get("link")
    
    sender = get_sender()
    
    if chat_id:
        # Direct send to specified chat
        await sender.send_alert(chat_id, level, "AFASA Alert", message, link)
    else:
        # Broadcast to all linked chats for this tenant
        async with AsyncSessionLocal() as session:
            await session.execute(f"SET app.tenant_id = '{tenant_id}'")
            result = await session.execute(select(TelegramLink))
            links = result.scalars().all()
            
            for tg_link in links:
                await sender.send_alert(tg_link.chat_id, level, "AFASA Alert", message, link)


async def handle_assessment_created(envelope: EventEnvelope):
    """Send notification when assessment is created"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    severity = data.get("severity", "low")
    hypotheses = data.get("hypotheses", [])
    
    # Only notify for medium/high severity
    if severity not in ["medium", "high"]:
        return
    
    level = "critical" if severity == "high" else "warn"
    
    # Build message
    issues = ", ".join([h.get("name", "unknown") for h in hypotheses[:3]])
    message = f"Plant health assessment: {severity.upper()}\n\nIssues detected: {issues}"
    
    # Broadcast
    sender = get_sender()
    async with AsyncSessionLocal() as session:
        await session.execute(f"SET app.tenant_id = '{tenant_id}'")
        result = await session.execute(select(TelegramLink))
        links = result.scalars().all()
        
        for tg_link in links:
            await sender.send_alert(tg_link.chat_id, level, "Plant Health Alert", message)


async def handle_rule_proposed(envelope: EventEnvelope):
    """Notify when AI proposes a rule requiring approval"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    if not data.get("requires_approval"):
        return
    
    intent_type = data.get("intent_type", "unknown")
    confidence = data.get("confidence", 0)
    
    message = f"AI Rule Proposal\n\nType: {intent_type}\nConfidence: {confidence:.0%}\n\nReply to approve or reject."
    
    sender = get_sender()
    async with AsyncSessionLocal() as session:
        await session.execute(f"SET app.tenant_id = '{tenant_id}'")
        result = await session.execute(select(TelegramLink))
        links = result.scalars().all()
        
        for tg_link in links:
            await sender.send_alert(tg_link.chat_id, "info", "AI Rule Proposal", message)


async def start_notification_subscriber():
    """Start listening for notification events"""
    event_bus = await get_event_bus()
    
    await event_bus.subscribe(
        Subjects.TELEGRAM_OUTBOUND,
        handle_telegram_outbound,
        queue="telegram-workers"
    )
    
    await event_bus.subscribe(
        Subjects.ASSESSMENT_CREATED,
        handle_assessment_created,
        queue="telegram-assessment"
    )
    
    await event_bus.subscribe(
        Subjects.RULE_PROPOSED,
        handle_rule_proposed,
        queue="telegram-rules"
    )
    
    print("Telegram notification subscriber started")
