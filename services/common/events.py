"""
AFASA 2.0 - NATS Event Bus
Standardized event publishing and subscription
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from dataclasses import dataclass, asdict
import nats
from nats.aio.client import Client as NATSClient

from .settings import get_settings


@dataclass
class EventEnvelope:
    event_id: str
    event_type: str
    tenant_id: str
    occurred_at: str
    producer: str
    data: dict
    correlation_id: Optional[str] = None
    
    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()
    
    @classmethod
    def from_json(cls, data: bytes) -> "EventEnvelope":
        d = json.loads(data.decode())
        return cls(**d)


class EventBus:
    def __init__(self):
        self._nc: Optional[NATSClient] = None
        self._js = None
    
    async def connect(self):
        settings = get_settings()
        self._nc = await nats.connect(settings.nats_url)
        self._js = self._nc.jetstream()
        
        # Ensure streams exist
        try:
            await self._js.add_stream(name="AFASA", subjects=["afasa.>"])
        except Exception:
            pass  # Stream may already exist
    
    async def disconnect(self):
        if self._nc:
            await self._nc.close()
    
    async def publish(
        self,
        subject: str,
        tenant_id: str,
        data: dict,
        producer: str,
        correlation_id: Optional[str] = None
    ):
        """Publish an event with standardized envelope"""
        envelope = EventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=subject,
            tenant_id=tenant_id,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            producer=producer,
            data=data,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        
        if self._js:
            await self._js.publish(subject, envelope.to_json())
        elif self._nc:
            await self._nc.publish(subject, envelope.to_json())
    
    async def subscribe(
        self,
        subject: str,
        handler: Callable[[EventEnvelope], Any],
        queue: Optional[str] = None
    ):
        """Subscribe to events with standardized handling"""
        async def message_handler(msg):
            try:
                envelope = EventEnvelope.from_json(msg.data)
                await handler(envelope)
                await msg.ack()
            except Exception as e:
                print(f"Error handling message: {e}")
                await msg.nak()
        
        if self._js:
            await self._js.subscribe(subject, cb=message_handler, queue=queue or "afasa-workers")
        elif self._nc:
            await self._nc.subscribe(subject, cb=message_handler, queue=queue or "afasa-workers")


# Singleton instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus


# Event subjects
class Subjects:
    SNAPSHOT_CREATED = "afasa.media.snapshot.created"
    DETECTION_CREATED = "afasa.vision.detection.created"
    ASSESSMENT_CREATED = "afasa.vision.assessment.created"
    TASK_GENERATED = "afasa.ops.task.generated"
    RULE_PROPOSED = "afasa.ops.rule.proposed"
    RULE_ACTIVATED = "afasa.ops.rule.activated"
    REPORT_REQUESTED = "afasa.report.requested"
    REPORT_READY = "afasa.report.ready"
    TELEGRAM_OUTBOUND = "afasa.notify.telegram.outbound"
    DEVICE_SYNCED = "afasa.tb.device.synced"
    DEVICE_COMMAND_REQUESTED = "afasa.tb.device.command.requested"
    DEVICE_COMMAND_COMPLETED = "afasa.tb.device.command.completed"
