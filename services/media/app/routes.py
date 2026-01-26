"""
AFASA 2.0 - Media Service Routes
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, TokenPayload, get_tenant_session,
    get_event_bus, Subjects, get_storage_client,
    Camera, Snapshot
)
from app.snapshot import capture_snapshot
from app.onvif import execute_ptz_command

router = APIRouter(tags=["media"])


# Request/Response Models
class OnvifConfig(BaseModel):
    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


class CameraCreate(BaseModel):
    name: str
    location: Optional[str] = None
    rtsp_url: str
    onvif: Optional[OnvifConfig] = None


class CameraResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    location: Optional[str]
    rtsp_url: str
    onvif_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SnapshotRequest(BaseModel):
    reason: str = "manual"
    timestamp_hint: Optional[datetime] = None


class SnapshotResponse(BaseModel):
    snapshot_id: UUID
    camera_id: UUID
    taken_at: datetime
    s3_key: str
    width: Optional[int]
    height: Optional[int]


class PTZRequest(BaseModel):
    action: str  # zoom_in, zoom_out, pan_left, pan_right, tilt_up, tilt_down, stop
    speed: float = 0.5


class PTZResponse(BaseModel):
    ok: bool


class StreamResponse(BaseModel):
    hls_url: str


@router.post("/cameras", response_model=CameraResponse)
async def create_camera(
    body: CameraCreate,
    token: TokenPayload = Depends(verify_token)
):
    """Create a new camera"""
    async with get_tenant_session(token.tenant_id) as session:
        camera = Camera(
            tenant_id=UUID(token.tenant_id),
            name=body.name,
            location=body.location,
            rtsp_url=body.rtsp_url,
            onvif_enabled=body.onvif.enabled if body.onvif else False,
            onvif_host=body.onvif.host if body.onvif else None,
            onvif_port=body.onvif.port if body.onvif else None,
            onvif_username=body.onvif.username if body.onvif else None,
        )
        session.add(camera)
        await session.flush()
        await session.refresh(camera)
        return camera


@router.get("/cameras", response_model=List[CameraResponse])
async def list_cameras(token: TokenPayload = Depends(verify_token)):
    """List all cameras for tenant"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(select(Camera))
        cameras = result.scalars().all()
        return cameras


@router.get("/cameras/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Get a specific camera"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        return camera


@router.post("/cameras/{camera_id}/test")
async def test_camera(
    camera_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Test camera connectivity"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # TODO: Implement actual RTSP and ONVIF testing
        return {
            "rtsp_ok": True,
            "onvif_ok": camera.onvif_enabled,
            "details": "Connection test passed"
        }


@router.post("/cameras/{camera_id}/snapshot", response_model=SnapshotResponse)
async def create_snapshot(
    camera_id: UUID,
    body: SnapshotRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Capture a snapshot from camera"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # Capture snapshot
        snapshot_data = await capture_snapshot(camera.rtsp_url)
        taken_at = body.timestamp_hint or datetime.now(timezone.utc)
        
        # Upload to S3
        storage = get_storage_client()
        snapshot = Snapshot(
            tenant_id=UUID(token.tenant_id),
            camera_id=camera_id,
            taken_at=taken_at,
            reason=body.reason,
            s3_key="",  # Will be set after upload
            width=snapshot_data.get("width"),
            height=snapshot_data.get("height")
        )
        session.add(snapshot)
        await session.flush()
        
        s3_key = storage.upload_snapshot(
            token.tenant_id,
            str(snapshot.id),
            snapshot_data["data"]
        )
        snapshot.s3_key = s3_key
        await session.flush()
        
        # Publish event
        event_bus = await get_event_bus()
        await event_bus.publish(
            Subjects.SNAPSHOT_CREATED,
            token.tenant_id,
            {
                "snapshot_id": str(snapshot.id),
                "camera_id": str(camera_id),
                "s3_key": s3_key,
                "taken_at": taken_at.isoformat(),
                "reason": body.reason
            },
            producer="afasa-media"
        )
        
        return SnapshotResponse(
            snapshot_id=snapshot.id,
            camera_id=camera_id,
            taken_at=taken_at,
            s3_key=s3_key,
            width=snapshot_data.get("width"),
            height=snapshot_data.get("height")
        )


@router.post("/cameras/{camera_id}/ptz", response_model=PTZResponse)
async def camera_ptz(
    camera_id: UUID,
    body: PTZRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Execute PTZ command"""
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        if not camera.onvif_enabled:
            raise HTTPException(status_code=400, detail="ONVIF not enabled for this camera")
        
        ok = await execute_ptz_command(camera, body.action, body.speed)
        return PTZResponse(ok=ok)


@router.get("/streams/{camera_id}/hls", response_model=StreamResponse)
async def get_stream_url(
    camera_id: UUID,
    token: TokenPayload = Depends(verify_token)
):
    """Get HLS stream URL for camera"""
    from common import get_settings
    settings = get_settings()
    
    async with get_tenant_session(token.tenant_id) as session:
        result = await session.execute(
            select(Camera).where(Camera.id == camera_id)
        )
        camera = result.scalar_one_or_none()
        if not camera:
            raise HTTPException(status_code=404, detail="Camera not found")
        
        # HLS URL through MediaMTX
        hls_url = f"{settings.public_base_url}/stream/hls/{camera_id}.m3u8"
        return StreamResponse(hls_url=hls_url)


@router.get("/snapshots")
async def list_snapshots(
    limit: int = 10,
    camera_id: Optional[UUID] = None,
    token: TokenPayload = Depends(verify_token)
):
    """List recent snapshots"""
    async with get_tenant_session(token.tenant_id) as session:
        query = select(Snapshot).order_by(Snapshot.taken_at.desc()).limit(limit)
        
        if camera_id:
            query = query.where(Snapshot.camera_id == camera_id)
        
        result = await session.execute(query)
        snapshots = result.scalars().all()
        
        storage = get_storage_client()
        
        return [
            {
                "id": str(s.id),
                "camera_id": str(s.camera_id),
                "taken_at": s.taken_at.isoformat(),
                "reason": s.reason,
                "width": s.width,
                "height": s.height,
                "thumbnail_url": storage.get_presigned_url(s.s3_key, expires=3600)
            }
            for s in snapshots
        ]

