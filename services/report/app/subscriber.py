"""
AFASA 2.0 - Report Request Subscriber
"""
import sys
sys.path.insert(0, '/app/services')

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func

from common import (
    get_event_bus, EventEnvelope, Subjects,
    get_admin_session, get_storage_client,
    Report, Detection, Assessment, Task, Snapshot, Tenant
)
from app.generate import generate_pdf_report, generate_xlsx_report


async def handle_report_requested(envelope: EventEnvelope):
    """Handle report request events - async generation"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    report_id = data.get("report_id")
    format_type = data.get("format", "pdf")
    range_from = datetime.fromisoformat(data.get("range_from"))
    range_to = datetime.fromisoformat(data.get("range_to"))
    
    print(f"Processing report {report_id} ({format_type}) for tenant {tenant_id}")
    
    storage = get_storage_client()
    
    try:
        async with get_admin_session() as session:
            # Set tenant context
            await session.execute(f"SET app.tenant_id = '{tenant_id}'")
            
            # Get report record
            result = await session.execute(
                select(Report).where(Report.id == UUID(report_id))
            )
            report = result.scalar_one_or_none()
            
            if not report:
                print(f"Report {report_id} not found")
                return
            
            # Idempotency: skip if already ready
            if report.status == "ready":
                print(f"Report {report_id} already ready, skipping")
                return
            
            # Update status to processing
            report.status = "processing"
            await session.commit()
            
            # Get tenant name
            tenant_result = await session.execute(
                select(Tenant).where(Tenant.id == UUID(tenant_id))
            )
            tenant = tenant_result.scalar_one_or_none()
            tenant_name = tenant.name if tenant else "Unknown"
            
            # Gather data
            det_result = await session.execute(
                select(Detection).where(
                    Detection.created_at >= range_from,
                    Detection.created_at <= range_to
                )
            )
            detections = [
                {
                    "id": str(d.id),
                    "camera_id": str(d.camera_id),
                    "label": d.label,
                    "confidence": d.confidence,
                    "created_at": d.created_at.isoformat()
                }
                for d in det_result.scalars().all()
            ]
            
            ass_result = await session.execute(
                select(Assessment).where(
                    Assessment.created_at >= range_from,
                    Assessment.created_at <= range_to
                )
            )
            assessments = [
                {
                    "id": str(a.id),
                    "camera_id": str(a.camera_id),
                    "severity": a.severity,
                    "hypotheses": a.hypotheses,
                    "created_at": a.created_at.isoformat()
                }
                for a in ass_result.scalars().all()
            ]
            
            task_result = await session.execute(select(Task))
            tasks = [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "priority": t.priority,
                    "status": t.status,
                    "due_at": t.due_at.isoformat() if t.due_at else None
                }
                for t in task_result.scalars().all()
            ]
            
            # Summary stats
            snapshot_count = await session.scalar(
                select(func.count(Snapshot.id)).where(
                    Snapshot.taken_at >= range_from,
                    Snapshot.taken_at <= range_to
                )
            )
            
            summary = {
                "total_snapshots": snapshot_count or 0,
                "total_detections": len(detections),
                "total_assessments": len(assessments),
                "open_tasks": len([t for t in tasks if t["status"] == "open"]),
                "completed_tasks": len([t for t in tasks if t["status"] == "done"])
            }
            
            # Generate report
            if format_type == "pdf":
                data_bytes = generate_pdf_report(
                    tenant_name, range_from, range_to,
                    summary, detections, assessments, tasks
                )
            else:
                data_bytes = generate_xlsx_report(
                    tenant_name, range_from, range_to,
                    detections, assessments, tasks
                )
            
            # Upload to MinIO
            s3_key = storage.upload_report(tenant_id, report_id, data_bytes, format_type)
            
            # Update report status
            report.s3_key = s3_key
            report.status = "ready"
            await session.commit()
            
            # Publish completion event
            event_bus = await get_event_bus()
            await event_bus.publish(
                Subjects.REPORT_READY,
                tenant_id,
                {
                    "report_id": report_id,
                    "s3_key": s3_key
                },
                producer="afasa-report-worker"
            )
            
            print(f"Report {report_id} completed successfully")
            
    except Exception as e:
        print(f"Error generating report {report_id}: {e}")
        # Update status to failed
        async with get_admin_session() as session:
            result = await session.execute(
                select(Report).where(Report.id == UUID(report_id))
            )
            report = result.scalar_one_or_none()
            if report:
                report.status = "failed"
                await session.commit()


async def start_report_subscriber():
    """Start listening for report request events"""
    event_bus = await get_event_bus()
    
    await event_bus.subscribe(
        Subjects.REPORT_REQUESTED,
        handle_report_requested,
        queue="report-workers"
    )
    
    print("Report subscriber started")
