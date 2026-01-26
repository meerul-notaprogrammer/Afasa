"""
AFASA 2.0 - Rate Limiter
Per-tenant rate limiting with cooldown and quiet hours support
"""
from datetime import datetime, time, timezone, timedelta
from typing import Tuple, Optional
import redis.asyncio as redis
import os


class RateLimiter:
    """Rate limiter for alerts and notifications"""
    
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    async def should_send(
        self,
        tenant_id: str,
        alert_type: str,
        max_daily: int = 50,
        cooldown_minutes: int = 30,
        quiet_hours_start: Optional[str] = None,  # "22:00"
        quiet_hours_end: Optional[str] = None      # "06:00"
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an alert should be sent based on rate limits.
        Returns: (should_send, skip_reason)
        """
        now = datetime.now(timezone.utc)
        
        # Check quiet hours
        if quiet_hours_start and quiet_hours_end:
            if self._in_quiet_hours(now, quiet_hours_start, quiet_hours_end):
                return False, "quiet_hours"
        
        # Check daily limit
        daily_key = f"afasa:alerts:{tenant_id}:count:{now.strftime('%Y-%m-%d')}"
        daily_count = await self.redis.get(daily_key)
        if daily_count and int(daily_count) >= max_daily:
            return False, "daily_limit"
        
        # Check cooldown
        cooldown_key = f"afasa:alerts:{tenant_id}:last:{alert_type}"
        last_sent = await self.redis.get(cooldown_key)
        if last_sent:
            last_time = datetime.fromisoformat(last_sent)
            elapsed = (now - last_time).total_seconds() / 60
            if elapsed < cooldown_minutes:
                return False, "cooldown"
        
        return True, None
    
    async def record_sent(self, tenant_id: str, alert_type: str):
        """Record that an alert was sent"""
        now = datetime.now(timezone.utc)
        
        # Increment daily counter
        daily_key = f"afasa:alerts:{tenant_id}:count:{now.strftime('%Y-%m-%d')}"
        await self.redis.incr(daily_key)
        await self.redis.expire(daily_key, 86400 * 2)  # Expire after 2 days
        
        # Record last sent time
        cooldown_key = f"afasa:alerts:{tenant_id}:last:{alert_type}"
        await self.redis.set(cooldown_key, now.isoformat())
        await self.redis.expire(cooldown_key, 86400)  # Expire after 1 day
    
    def _in_quiet_hours(self, now: datetime, start: str, end: str) -> bool:
        """Check if current time is within quiet hours"""
        current_time = now.time()
        start_time = time.fromisoformat(start)
        end_time = time.fromisoformat(end)
        
        if start_time <= end_time:
            # Normal range (e.g., 09:00 - 17:00)
            return start_time <= current_time <= end_time
        else:
            # Overnight range (e.g., 22:00 - 06:00)
            return current_time >= start_time or current_time <= end_time
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
