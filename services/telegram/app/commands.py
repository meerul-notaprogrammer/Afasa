"""
AFASA 2.0 - Telegram Bot Commands
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select
import httpx
import sys
sys.path.insert(0, '/app/services')

from common import (
    get_settings, get_tenant_session, get_storage_client,
    Task, Camera, TelegramLink
)
from app.send import get_sender

settings = get_settings()


async def handle_command(
    chat_id: str,
    command: str,
    args: str,
    tenant_id: Optional[str] = None
) -> str:
    """
    Process a bot command and return response message.
    """
    cmd = command.lower().strip("/")
    
    if cmd == "start":
        return "👋 Welcome to AFASA Bot!\n\nUse /link <code> to connect your account.\n\nCommands:\n/status - Current status\n/today - Today's tasks\n/help - Show help"
    
    if cmd == "help":
        return """🌱 <b>AFASA Bot Commands</b>

/status - View farm status
/today - Today's tasks
/snapshot <camera> - Take snapshot
/report daily|weekly - Generate report
/ask <question> - Ask AI

Use /link <code> to connect your account."""
    
    if cmd == "link":
        # Link command handled separately in routes
        return "Linking..."
    
    # Commands below require tenant association
    if not tenant_id:
        return "❌ Please link your account first using /link <code>"
    
    if cmd == "status":
        return await cmd_status(tenant_id)
    
    if cmd == "today":
        return await cmd_today_tasks(tenant_id)
    
    if cmd == "snapshot":
        return await cmd_snapshot(tenant_id, args)
    
    if cmd == "report":
        return await cmd_report(tenant_id, args)
    
    if cmd == "ask":
        return await cmd_ask(tenant_id, args)
    
    return f"❓ Unknown command: /{cmd}\n\nType /help for available commands."


async def cmd_status(tenant_id: str) -> str:
    """Get current farm status"""
    async with get_tenant_session(tenant_id) as session:
        # Count cameras
        cameras_result = await session.execute(select(Camera))
        cameras = cameras_result.scalars().all()
        
        # Count open tasks
        tasks_result = await session.execute(
            select(Task).where(Task.status == "open")
        )
        open_tasks = len(tasks_result.scalars().all())
        
        return f"""📊 <b>Farm Status</b>

🎥 Cameras: {len(cameras)}
📋 Open Tasks: {open_tasks}
⏰ Last Check: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC

Use /today to see today's tasks."""


async def cmd_today_tasks(tenant_id: str) -> str:
    """Get today's tasks"""
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Task).where(Task.status == "open").order_by(Task.priority.asc()).limit(10)
        )
        tasks = result.scalars().all()
        
        if not tasks:
            return "✅ No open tasks for today!"
        
        lines = ["📋 <b>Today's Tasks</b>\n"]
        for task in tasks:
            priority_emoji = ["🔴", "🟠", "🟡", "🟢", "⚪"][min(task.priority - 1, 4)]
            lines.append(f"{priority_emoji} {task.title}")
        
        return "\n".join(lines)


async def cmd_snapshot(tenant_id: str, camera_name: str) -> str:
    """Request a camera snapshot"""
    if not camera_name:
        return "Usage: /snapshot <camera_name>"
    
    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.name.ilike(f"%{camera_name}%"))
        )
        camera = result.scalar_one_or_none()
        
        if not camera:
            return f"❌ Camera '{camera_name}' not found"
        
        # TODO: Trigger actual snapshot via HTTP call to media service
        return f"📸 Snapshot requested for {camera.name}\n\nProcessing..."


async def cmd_report(tenant_id: str, report_type: str) -> str:
    """Request a report"""
    valid_types = ["daily", "weekly", "monthly"]
    
    if not report_type or report_type.lower() not in valid_types:
        return f"Usage: /report {{{', '.join(valid_types)}}}"
    
    # TODO: Trigger actual report generation
    return f"📄 Generating {report_type} report...\n\nYou'll receive it shortly."


async def cmd_ask(tenant_id: str, question: str) -> str:
    """Ask AI a question"""
    if not question:
        return "Usage: /ask <your question>"
    
    # TODO: Integrate with Gemini for general Q&A
    return f"🤔 Let me think about: {question}\n\n(AI integration coming soon)"
