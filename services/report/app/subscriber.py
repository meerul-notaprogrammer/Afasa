"""
AFASA 2.0 - Report Request Subscriber
"""
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus, EventEnvelope, Subjects


async def handle_report_requested(envelope: EventEnvelope):
    """Handle report request events"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    report_id = data.get("report_id")
    format = data.get("format", "pdf")
    date_from = data.get("from")
    date_to = data.get("to")
    
    print(f"Report requested: {report_id} ({format}) for tenant {tenant_id}")
    
    # Report generation is handled synchronously in the API route
    # This subscriber could be used for async/background generation


async def start_report_subscriber():
    """Start listening for report request events"""
    event_bus = await get_event_bus()
    
    await event_bus.subscribe(
        Subjects.REPORT_REQUESTED,
        handle_report_requested,
        queue="report-workers"
    )
    
    print("Report subscriber started")
