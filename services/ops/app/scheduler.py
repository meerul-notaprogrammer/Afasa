"""
AFASA 2.0 - APScheduler-based Job Scheduler
"""
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    get_settings, get_event_bus, Subjects,
    get_storage_client, Tenant, Camera, Snapshot, TenantSettings
)
from common.db import AsyncSessionLocal

scheduler = AsyncIOScheduler()


async def daily_assessment_job():
    """
    Daily plant health check job.
    Triggers snapshots for all cameras across all tenants.
    """
    print(f"[{datetime.now(timezone.utc)}] Running daily assessment job")
    
    async with AsyncSessionLocal() as session:
        # Get all tenants
        result = await session.execute(select(Tenant))
        tenants = result.scalars().all()
        
        for tenant in tenants:
            # Get cameras for this tenant
            await session.execute(f"SET app.tenant_id = '{tenant.id}'")
            cameras_result = await session.execute(select(Camera))
            cameras = cameras_result.scalars().all()
            
            for camera in cameras:
                # Publish snapshot request event
                event_bus = await get_event_bus()
                await event_bus.publish(
                    "afasa.ops.snapshot.request",
                    str(tenant.id),
                    {
                        "camera_id": str(camera.id),
                        "reason": "scheduled",
                        "job": "daily_assessment"
                    },
                    producer="afasa-ops"
                )
            
            print(f"Triggered {len(cameras)} camera snapshots for tenant {tenant.id}")


async def retention_cleanup_job():
    """
    Daily cleanup job for expired data.
    Removes snapshots/reports older than retention settings.
    """
    print(f"[{datetime.now(timezone.utc)}] Running retention cleanup job")
    
    storage = get_storage_client()
    
    async with AsyncSessionLocal() as session:
        # Get all tenant settings
        result = await session.execute(select(TenantSettings))
        all_settings = result.scalars().all()
        
        for settings in all_settings:
            tenant_id = str(settings.tenant_id)
            
            # Cleanup snapshots
            snapshot_cutoff = datetime.now(timezone.utc) - timedelta(
                days=settings.retention_snapshots_days
            )
            
            await session.execute(f"SET app.tenant_id = '{tenant_id}'")
            
            snapshot_result = await session.execute(
                select(Snapshot).where(Snapshot.taken_at < snapshot_cutoff)
            )
            old_snapshots = snapshot_result.scalars().all()
            
            for snapshot in old_snapshots:
                try:
                    storage.delete_object(snapshot.s3_key)
                    await session.delete(snapshot)
                except Exception as e:
                    print(f"Failed to delete snapshot {snapshot.id}: {e}")
            
            if old_snapshots:
                print(f"Cleaned up {len(old_snapshots)} old snapshots for tenant {tenant_id}")


async def start_scheduler():
    """Start the APScheduler"""
    # Daily assessment at 8 AM
    scheduler.add_job(
        daily_assessment_job,
        CronTrigger(hour=8, minute=0),
        id="daily_assessment",
        replace_existing=True
    )
    
    # Retention cleanup at 2 AM
    scheduler.add_job(
        retention_cleanup_job,
        CronTrigger(hour=2, minute=0),
        id="retention_cleanup",
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started with daily_assessment and retention_cleanup jobs")


async def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
    print("Scheduler stopped")


async def run_job_now(job_id: str) -> bool:
    """Manually trigger a job"""
    job = scheduler.get_job(job_id)
    if job:
        await job.func()
        return True
    return False
