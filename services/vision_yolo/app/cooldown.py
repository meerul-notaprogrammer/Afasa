"""
AFASA 2.0 - Detection Cooldown Policy
Prevents alert spam using Redis-based cooldowns
"""
import time
from typing import Tuple
import redis.asyncio as redis
import sys
sys.path.insert(0, '/app/services')

from common import get_settings

settings = get_settings()

# Default cooldown: 1 hour
DEFAULT_COOLDOWN_SEC = 3600

# Minimum confidence threshold
MIN_CONFIDENCE = 0.5

_redis: redis.Redis = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


def cooldown_key(tenant_id: str, camera_id: str, label: str) -> str:
    """Generate Redis key for cooldown tracking"""
    return f"cooldown:{tenant_id}:{camera_id}:{label}"


async def check_cooldown(
    tenant_id: str,
    camera_id: str,
    label: str,
    confidence: float,
    cooldown_sec: int = DEFAULT_COOLDOWN_SEC,
    min_confidence: float = MIN_CONFIDENCE
) -> Tuple[bool, int]:
    """
    Check if detection should trigger alert.
    Returns (should_alert, cooldown_remaining_sec).
    """
    # Below minimum confidence - never alert
    if confidence < min_confidence:
        return False, 0
    
    r = await get_redis()
    key = cooldown_key(tenant_id, camera_id, label)
    
    last_alert = await r.get(key)
    
    if last_alert is None:
        # No previous alert - should alert
        return True, 0
    
    last_alert_time = float(last_alert.decode())
    elapsed = time.time() - last_alert_time
    remaining = int(cooldown_sec - elapsed)
    
    if remaining <= 0:
        # Cooldown expired - should alert
        return True, 0
    
    # Still in cooldown - don't alert
    return False, remaining


async def update_cooldown(
    tenant_id: str,
    camera_id: str,
    label: str,
    cooldown_sec: int = DEFAULT_COOLDOWN_SEC
):
    """Update last alert time for cooldown tracking"""
    r = await get_redis()
    key = cooldown_key(tenant_id, camera_id, label)
    await r.set(key, str(time.time()), ex=cooldown_sec)


async def clear_cooldown(
    tenant_id: str,
    camera_id: str,
    label: str
):
    """Clear cooldown (for manual reset)"""
    r = await get_redis()
    key = cooldown_key(tenant_id, camera_id, label)
    await r.delete(key)
