"""
AFASA 2.0 - Report Request Subscriber
"""
import asyncio
import sys
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func

sys.path.insert(0, '/app/services')

from common import (
    get_event_bus, EventEnvelope, Subjects, get_tenant_session,
    Report, Detection, Assessment, Task, Snapshot, Tenant,
    get_storage_client
)
from app.generate import generate_pdf_report, generate_xlsx_report


async def handle_report_requested(envelope: EventEnvelope):
    """Handle report request events"""
    data = envelope.data
    tenant_id = envelope.tenant_id
    
    report_id = data.get("report_id")
    format_type = data.get("format", "pdf")
    
    # Parse dates from ISO strings
    try:
        range_from = datetime.fromisoformat(data.get("range_from"))
        range_to = datetime.fromisoformat(data.get("range_to"))
    except (ValueError, TypeError):
        print(f"Invalid date format for report {report_id}")
        return

    print(f"Report requested: {report_id} ({format_type}) for tenant {tenant_id}")
    
    try:
        async with get_tenant_session(tenant_id) as session:
            # Get report record
            result = await session.execute(
                select(Report).where(Report.id == UUID(report_id))
            )
            report = result.scalar_one_or_none()

            if not report:
                print(f"Report {report_id} not found")
                return

            try:
                report.status = "processing"
                await session.flush()

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

                # Generate report (CPU bound, run in executor)
                loop = asyncio.get_running_loop()

                if format_type == "pdf":
                    report_data = await loop.run_in_executor(
                        None,
                        generate_pdf_report,
                        tenant_name, range_from, range_to,
                        summary, detections, assessments, tasks
                    )
                else:
                    report_data = await loop.run_in_executor(
                        None,
                        generate_xlsx_report,
                        tenant_name, range_from, range_to,
                        detections, assessments, tasks
                    )

                # Upload to S3 (Network bound but sync client, run in executor)
                storage = get_storage_client()
                s3_key = await loop.run_in_executor(
                    None,
                    storage.upload_report,
                    tenant_id, str(report.id), report_data, format_type
                )

                # Update report status
                report.s3_key = s3_key
                report.status = "ready"
                await session.flush()

                # Publish completion event
                event_bus = await get_event_bus()
                await event_bus.publish(
                    Subjects.REPORT_READY,
                    tenant_id,
                    {
                        "report_id": str(report.id),
                        "s3_key": s3_key
                    },
                    producer="afasa-report"
                )

                print(f"Report generated: {report_id}")

            except Exception as e:
                print(f"Error generating report {report_id}: {e}")
                report.status = "failed"
                # Session will commit "failed" status on exit

    except Exception as e:
        print(f"Critical error in report subscriber for {report_id}: {e}")


async def start_report_subscriber():
    """Start listening for report request events"""
    event_bus = await get_event_bus()
    
    await event_bus.subscribe(
        Subjects.REPORT_REQUESTED,
        handle_report_requested,
        queue="report-workers"
    )
    
    print("Report subscriber started")
