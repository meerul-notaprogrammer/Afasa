"""
AFASA 2.0 - Retention Cleaner Service
Daily cleanup of expired snapshots and reports based on tenant settings
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import structlog

# Add common to path
sys.path.insert(0, '/app/services')

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from common import get_settings, get_storage_client, get_audit_service
from common.db import get_admin_session
from common.models import Tenant, TenantSettings, Snapshot, Report

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


async def cleanup_tenant_data(tenant_id: str, settings: TenantSettings):
    """Cleanup expired data for a specific tenant"""
    now = datetime.now(timezone.utc)
    storage = get_storage_client()
    audit = get_audit_service()
    
    # Calculate cutoff dates
    snapshot_cutoff = now - timedelta(days=settings.retention_snapshots_days)
    report_cutoff = now - timedelta(days=settings.retention_reports_days)
    
    deleted_snapshots = 0
    deleted_reports = 0
    
    try:
        # Get expired snapshots
        async with get_admin_session() as session:
            from sqlalchemy import select, delete
            
            # Find expired snapshots
            result = await session.execute(
                select(Snapshot)
                .where(Snapshot.tenant_id == tenant_id)
                .where(Snapshot.created_at < snapshot_cutoff)
            )
            expired_snapshots = result.scalars().all()
            
            # Delete from MinIO
            for snapshot in expired_snapshots:
                try:
                    storage.delete_object(snapshot.s3_key)
                    deleted_snapshots += 1
                except Exception as e:
                    logger.warning("failed_delete_snapshot", 
                                   snapshot_id=str(snapshot.id), 
                                   error=str(e))
            
            # Delete from database
            if expired_snapshots:
                await session.execute(
                    delete(Snapshot)
                    .where(Snapshot.tenant_id == tenant_id)
                    .where(Snapshot.created_at < snapshot_cutoff)
                )
            
            # Find expired reports
            result = await session.execute(
                select(Report)
                .where(Report.tenant_id == tenant_id)
                .where(Report.created_at < report_cutoff)
            )
            expired_reports = result.scalars().all()
            
            # Delete from MinIO
            for report in expired_reports:
                if report.s3_key:
                    try:
                        storage.delete_object(report.s3_key)
                        deleted_reports += 1
                    except Exception as e:
                        logger.warning("failed_delete_report",
                                       report_id=str(report.id),
                                       error=str(e))
            
            # Delete from database
            if expired_reports:
                await session.execute(
                    delete(Report)
                    .where(Report.tenant_id == tenant_id)
                    .where(Report.created_at < report_cutoff)
                )
            
            await session.commit()
        
        # Audit log
        if deleted_snapshots > 0 or deleted_reports > 0:
            await audit.log(
                tenant_id=tenant_id,
                actor_type="system",
                action="retention.cleanup",
                target_type="tenant",
                target_id=tenant_id,
                reason=f"Retention policy cleanup: {deleted_snapshots} snapshots, {deleted_reports} reports deleted"
            )
        
        logger.info("tenant_cleanup_complete",
                    tenant_id=tenant_id,
                    deleted_snapshots=deleted_snapshots,
                    deleted_reports=deleted_reports)
        
    except Exception as e:
        logger.error("tenant_cleanup_failed",
                     tenant_id=tenant_id,
                     error=str(e))


async def run_cleanup():
    """Run cleanup for all tenants"""
    logger.info("starting_retention_cleanup")
    
    try:
        async with get_admin_session() as session:
            from sqlalchemy import select
            
            # Get all tenants with settings
            result = await session.execute(
                select(Tenant, TenantSettings)
                .join(TenantSettings, Tenant.id == TenantSettings.tenant_id, isouter=True)
            )
            rows = result.all()
        
        for tenant, settings in rows:
            if settings:
                await cleanup_tenant_data(str(tenant.id), settings)
            else:
                logger.warning("tenant_missing_settings", tenant_id=str(tenant.id))
        
        logger.info("retention_cleanup_complete", tenants_processed=len(rows))
        
    except Exception as e:
        logger.error("retention_cleanup_failed", error=str(e))


def main():
    """Main entry point"""
    logger.info("retention_cleaner_starting")
    
    # Create scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    
    # Schedule cleanup at 2 AM UTC daily
    scheduler.add_job(
        run_cleanup,
        CronTrigger(hour=2, minute=0),
        id="daily_cleanup",
        name="Daily Retention Cleanup"
    )
    
    # Also run on startup after a delay
    scheduler.add_job(
        run_cleanup,
        "date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=30),
        id="startup_cleanup",
        name="Startup Cleanup"
    )
    
    scheduler.start()
    
    logger.info("retention_cleaner_started", next_run="02:00 UTC daily")
    
    # Keep running
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("retention_cleaner_stopped")


if __name__ == "__main__":
    main()
