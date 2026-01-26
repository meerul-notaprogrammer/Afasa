"""
AFASA 2.0 - Telegram Message Sender
"""
import httpx
from typing import Optional, Dict, Any
import sys
sys.path.insert(0, '/app/services')

from common import get_settings

settings = get_settings()


class TelegramSender:
    def __init__(self):
        self._token = settings.telegram_bot_token
        self._base_url = f"https://api.telegram.org/bot{self._token}"
    
    async def send_message(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a text message"""
        if not self._token:
            print("Telegram bot token not configured")
            return False
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/sendMessage",
                    json=payload,
                    timeout=10.0
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None
    ) -> bool:
        """Send a photo with optional caption"""
        if not self._token:
            return False
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url
        }
        
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/sendPhoto",
                    json=payload,
                    timeout=30.0
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"Failed to send Telegram photo: {e}")
            return False
    
    async def send_alert(
        self,
        chat_id: str,
        level: str,
        title: str,
        message: str,
        link: Optional[str] = None
    ) -> bool:
        """Send a formatted alert message"""
        emoji = {
            "info": "ℹ️",
            "warn": "⚠️",
            "critical": "🚨"
        }.get(level, "📢")
        
        text = f"{emoji} <b>{title}</b>\n\n{message}"
        
        if link:
            text += f"\n\n🔗 <a href=\"{link}\">View Details</a>"
        
        return await self.send_message(chat_id, text)


_sender: TelegramSender = None


def get_sender() -> TelegramSender:
    global _sender
    if _sender is None:
        _sender = TelegramSender()
    return _sender
