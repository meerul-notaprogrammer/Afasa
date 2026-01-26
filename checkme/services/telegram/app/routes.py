"""
AFASA 2.0 - Telegram Webhook Routes
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
import secrets
import sys
sys.path.insert(0, '/app/services')

from common import get_settings, get_tenant_session, TelegramLink
from common.db import AsyncSessionLocal
from app.send import get_sender
from app.commands import handle_command

router = APIRouter(tags=["telegram"])
settings = get_settings()


class WebhookUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


class LinkRequest(BaseModel):
    code: str
    chat_id: str


# In-memory link codes (should be Redis in production)
_link_codes: Dict[str, str] = {}  # code -> tenant_id


def generate_link_code(tenant_id: str) -> str:
    """Generate a one-time link code"""
    code = secrets.token_urlsafe(8)[:8].upper()
    _link_codes[code] = tenant_id
    return code


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Handle Telegram webhook updates.
    Verify secret token and process commands.
    """
    # Verify webhook secret
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    body = await request.json()
    update = WebhookUpdate(**body)
    
    sender = get_sender()
    
    # Handle message
    if update.message:
        chat_id = str(update.message.get("chat", {}).get("id", ""))
        text = update.message.get("text", "")
        
        if not chat_id or not text:
            return {"ok": True}
        
        # Check if it's a command
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            # Handle /link command specially
            if command.lower() == "/link" and args:
                code = args.strip().upper()
                tenant_id = _link_codes.get(code)
                
                if tenant_id:
                    # Create link
                    async with AsyncSessionLocal() as session:
                        link = TelegramLink(
                            tenant_id=UUID(tenant_id),
                            chat_id=chat_id,
                            linked_at=datetime.now(timezone.utc)
                        )
                        session.add(link)
                        await session.commit()
                    
                    del _link_codes[code]
                    await sender.send_message(
                        chat_id,
                        "✅ Account linked successfully!\n\nYou'll now receive notifications here."
                    )
                else:
                    await sender.send_message(
                        chat_id,
                        "❌ Invalid or expired link code.\n\nPlease request a new code from the portal."
                    )
                return {"ok": True}
            
            # Look up tenant for this chat
            tenant_id = None
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(TelegramLink).where(TelegramLink.chat_id == chat_id)
                )
                link = result.scalar_one_or_none()
                if link:
                    tenant_id = str(link.tenant_id)
            
            # Process command
            response = await handle_command(chat_id, command, args, tenant_id)
            await sender.send_message(chat_id, response)
    
    # Handle callback query (inline button presses)
    if update.callback_query:
        callback_id = update.callback_query.get("id")
        data = update.callback_query.get("data", "")
        chat_id = str(update.callback_query.get("message", {}).get("chat", {}).get("id", ""))
        
        # TODO: Handle rule approval/rejection callbacks
        
    return {"ok": True}


@router.post("/link/generate")
async def generate_link(
    tenant_id: str
):
    """Generate a one-time link code for Telegram association"""
    code = generate_link_code(tenant_id)
    return {
        "code": code,
        "instruction": f"Send /link {code} to the AFASA bot"
    }


@router.get("/links")
async def list_links(tenant_id: str):
    """List Telegram links for a tenant"""
    async with AsyncSessionLocal() as session:
        await session.execute(f"SET app.tenant_id = '{tenant_id}'")
        result = await session.execute(select(TelegramLink))
        links = result.scalars().all()
        return [
            {
                "id": str(link.id),
                "chat_id": link.chat_id,
                "linked_at": link.linked_at.isoformat()
            }
            for link in links
        ]
