"""
AFASA 2.0 - Report Service Routes
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, TokenPayload, get_tenant_session,
    get_event_bus, Subjects, get_storage_client,
    Report, Detection, Assessment, Task, Snapshot, Tenant
)
from app.generate import generate_pdf_report, generate_xlsx_report

router = APIRouter(tags=["report"])


class ReportRequest(BaseModel):
    range_from: Optional[datetime] = None
    range_to: Optional[datetime] = None
    format: str = "pdf"  # pdf | xlsx
    type: str = "daily"  # daily | weekly | monthly | custom


class ReportResponse(BaseModel):
    report_id: UUID
    s3_key: Optional[str]
    status: str
    
    class Config:
        from_attributes = True


class ReportDownload(BaseModel):
    download_url: str
    format: str
    range_from: datetime
    range_to: datetime


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    body: ReportRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Generate a new report"""
    now = datetime.now(timezone.utc)
    
    # Calculate date range based on type
    if body.type == "daily":
        range_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        range_to = now
    elif body.type == "weekly":
        range_from = now - timedelta(days=7)
        range_to = now
    elif body.type == "monthly":
        range_from = now - timedelta(days=30)
        range_to = now
    elif body.type == "custom":
        if not body.range_from or not body.range_to:
            raise HTTPException(status_code=400, detail="Custom range requires from/to dates")
        range_from = body.range_from
        range_to = body.range_to
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    storage = get_storage_client()
    
    async with get_tenant_session(token.tenant_id) as session:
        # Get tenant name
        tenant_result = await session.execute(
            select(Tenant).where(Tenant.id == UUID(token.tenant_id))
        )
        tenant = tenant_result.scalar_one_or_none()
        tenant_name = tenant.name if tenant else "Unknown"
        
        # Create report record
        report = Report(
            tenant_id=UUID(token.tenant_id),
            format=body.format,
            range_from=range_from,
            range_to=range_to,
            status="processing"
        )
        session.add(report)
        await session.flush()
        
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
        if body.format == "pdf":
            data = generate_pdf_report(
                tenant_name, range_from, range_to,
                summary, detections, assessments, tasks
            )
        else:
            data = generate_xlsx_report(
                tenant_name, range_from, range_to,
                detections, assessments, tasks
            )
        
        # Upload to S3
        s3_key = storage.upload_report(token.tenant_id, str(report.id), data, body.format)
        
        report.s3_key = s3_key
        report.status = "ready"
        await session.flush()
        
        # Publish event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.REPORT_READY,
            token.tenant_id,
            {
                "report_id": str(report.id),
                "s3_key": s3_key
            },
            producer="afasa-report"
        )
        
        return report


@router.get("/reports/{report_id}", response_model=ReportDownload)
async def get_report(
    report_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Get report download URL"""
    storage = get_storage_client()
    
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report.status != "ready":
            raise HTTPException(status_code=400, detail=f"Report not ready: {report.status}")
        
        download_url = storage.get_presigned_url(report.s3_key)
        
        return ReportDownload(
            download_url=download_url,
            format=report.format,
            range_from=report.range_from,
            range_to=report.range_to
        )


@router.get("/reports")
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    token: TokenPayload = Depends(verify_token)
):
    """List all reports for tenant"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Report)
            .order_by(Report.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        reports = result.scalars().all()
        
        return [
            {
                "id": str(r.id),
                "format": r.format,
                "status": r.status,
                "range_from": r.range_from.isoformat(),
                "range_to": r.range_to.isoformat(),
                "created_at": r.created_at.isoformat()
            }
            for r in reports
        ]

