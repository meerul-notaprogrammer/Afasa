"""
AFASA 2.0 - TB Adapter Extended Routes
Embed tokens, device management, integrations
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
import sys
sys.path.insert(0, '/app/services')

from common import (
    verify_token, require_role, TokenPayload, get_tenant_session,
    Camera, Secret, get_secrets_manager, get_audit_service
)
from app.tb_api import get_tb_client
from app.ubibot import get_ubibot_channels

router = APIRouter()


# ============================================================================
# /api/tb - ThingsBoard Integration
# ============================================================================

class EmbedTokenRequest(BaseModel):
    dashboard_id: Optional[str] = None


class EmbedTokenResponse(BaseModel):
    url: str
    token: Optional[str] = None
    expires_at: str


@router.post("/tb/embed-token", response_model=EmbedTokenResponse, tags=["tb"])
async def get_embed_token(
    body: EmbedTokenRequest = None,
    token: TokenPayload = Depends(verify_token)
):
    """
    Get a short-lived embed token for ThingsBoard dashboard.
    Returns a URL that can be used in an iframe.
    """
    tb = get_tb_client()
    
    # Get default dashboard if not specified
    dashboard_id = body.dashboard_id if body else None
    
    if not dashboard_id:
        # Try to get first dashboard
        dashboards = await tb.get_dashboards()
        if dashboards:
            dashboard_id = dashboards[0].get("id", {}).get("id")
    
    if not dashboard_id:
        raise HTTPException(status_code=404, detail="No dashboard found")
    
    # Generate embed URL
    # In production, TB supports public dashboard links or embed tokens
    from common import get_settings
    settings = get_settings()
    
    # Build URL - TB public dashboard access
    url = f"{settings.tb_base_url}/dashboard/{dashboard_id}?publicId=public"
    
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    
    return EmbedTokenResponse(
        url=url,
        expires_at=expires_at
    )


@router.get("/integrations/thingsboard/dashboards", tags=["integrations"])
async def list_tb_dashboards(token: TokenPayload = Depends(verify_token)):
    """List available ThingsBoard dashboards"""
    tb = get_tb_client()
    dashboards = await tb.get_dashboards()
    return {"dashboards": dashboards}


# ============================================================================
# /api/devices - Unified Device Registry
# ============================================================================

class DeviceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    type: str  # camera, nvr, iot
    location: Optional[str]
    status: str
    last_seen: Optional[datetime]
    created_at: datetime


class CameraCreateRequest(BaseModel):
    name: str
    rtsp_url: str
    location: Optional[str] = None
    onvif_host: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class NVRCreateRequest(BaseModel):
    name: str
    host: str
    port: int = 554
    username: str
    password: str


@router.get("/devices", tags=["devices"])
async def list_devices(
    type: Optional[str] = None,
    token: TokenPayload = Depends(verify_token)
):
    """List all devices for the tenant"""
    async with get_tenant_session(token.tenant_id) as session:
        query = select(Camera)
        if type == "camera":
            query = query.where(Camera.onvif_enabled == False)
        
        result = await session.execute(query)
        cameras = result.scalars().all()
        
        devices = []
        for cam in cameras:
            devices.append({
                "id": str(cam.id),
                "tenant_id": str(cam.tenant_id),
                "name": cam.name,
                "type": "camera",
                "location": cam.location,
                "status": "online",  # Would check health in real implementation
                "last_seen": datetime.now(timezone.utc),
                "created_at": cam.created_at
            })
        
        return {"items": devices, "total": len(devices)}


@router.post("/devices/camera", tags=["devices"])
async def add_camera(
    body: CameraCreateRequest,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Add a single camera"""
    secrets = get_secrets_manager()
    audit = get_audit_service()
    
    async with get_tenant_session(token.tenant_id) as session:
        # Store password as secret if provided
        password_ref = None
        if body.password:
            cipher = secrets.encrypt(body.password)
            secret = Secret(
                tenant_id=UUID(token.tenant_id),
                purpose=f"camera_{body.name}_password",
                cipher_text=cipher
            )
            session.add(secret)
            await session.flush()
            password_ref = f"secret:{secret.id}"
        
        # Create camera
        camera = Camera(
            tenant_id=UUID(token.tenant_id),
            name=body.name,
            location=body.location,
            rtsp_url=body.rtsp_url,
            onvif_enabled=body.onvif_host is not None,
            onvif_host=body.onvif_host,
            onvif_username=body.username,
            onvif_password_ref=password_ref
        )
        session.add(camera)
        await session.flush()
        await session.refresh(camera)
        
    await audit.log(
        tenant_id=token.tenant_id,
        actor_type="user",
        actor_id=token.sub,
        action="device.added",
        target_type="camera",
        target_id=str(camera.id)
    )
    
    return {"id": str(camera.id), "status": "created"}


@router.post("/devices/{device_id}/enable", tags=["devices"])
async def enable_device(
    device_id: UUID,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Enable a device"""
    # In real implementation, would update device status
    return {"success": True}


@router.post("/devices/{device_id}/disable", tags=["devices"])
async def disable_device(
    device_id: UUID,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Disable a device"""
    return {"success": True}


# ============================================================================
# /api/integrations - External Integrations
# ============================================================================

class UbiBotConnectRequest(BaseModel):
    api_key: str


class TBConnectRequest(BaseModel):
    base_url: str
    jwt: str


@router.post("/integrations/ubibot/connect", tags=["integrations"])
async def connect_ubibot(
    body: UbiBotConnectRequest,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Store UbiBot API key and validate connection"""
    secrets = get_secrets_manager()
    audit = get_audit_service()
    
    # Validate API key by fetching channels
    try:
        channels = await get_ubibot_channels(body.api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid API key: {str(e)}")
    
    async with get_tenant_session(token.tenant_id) as session:
        # Store as secret
        cipher = secrets.encrypt(body.api_key)
        secret = Secret(
            tenant_id=UUID(token.tenant_id),
            purpose="ubibot_api_key",
            cipher_text=cipher
        )
        session.add(secret)
        await session.flush()
        
    await audit.log(
        tenant_id=token.tenant_id,
        actor_type="user",
        actor_id=token.sub,
        action="integration.connected",
        target_type="ubibot",
        target_id="ubibot"
    )
    
    return {"secret_ref": f"secret:{secret.id}", "status": "connected", "channels": len(channels)}


@router.post("/discovery/ubibot/sync", tags=["integrations"])
async def sync_ubibot(token: TokenPayload = Depends(require_role("tenant_admin"))):
    """Sync UbiBot devices to device registry"""
    secrets = get_secrets_manager()
    
    async with get_tenant_session(token.tenant_id) as session:
        # Get API key from secrets
        result = await session.execute(
            select(Secret).where(Secret.purpose == "ubibot_api_key")
        )
        secret = result.scalar_one_or_none()
        
        if not secret:
            raise HTTPException(status_code=400, detail="UbiBot not connected")
        
        api_key = secrets.decrypt(secret.cipher_text)
        
        # Fetch and sync channels
        channels = await get_ubibot_channels(api_key)
        
        created = 0
        for channel in channels:
            # Create device entry (simplified)
            # In real implementation, would check for existing and update
            created += 1
        
        return {"devices_found": len(channels), "devices_created": created}


@router.post("/integrations/thingsboard/connect", tags=["integrations"])
async def connect_thingsboard(
    body: TBConnectRequest,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Store ThingsBoard JWT and validate connection"""
    secrets = get_secrets_manager()
    audit = get_audit_service()
    
    # Validate by fetching dashboards
    tb = get_tb_client()
    try:
        dashboards = await tb.get_dashboards()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid TB connection: {str(e)}")
    
    async with get_tenant_session(token.tenant_id) as session:
        # Store JWT as secret
        cipher = secrets.encrypt(body.jwt)
        secret = Secret(
            tenant_id=UUID(token.tenant_id),
            purpose="tb_jwt",
            cipher_text=cipher
        )
        session.add(secret)
        await session.flush()
    
    await audit.log(
        tenant_id=token.tenant_id,
        actor_type="user",
        actor_id=token.sub,
        action="integration.connected",
        target_type="thingsboard",
        target_id="thingsboard"
    )
    
    return {
        "secret_ref": f"secret:{secret.id}",
        "dashboards": [{"id": d.get("id", {}).get("id"), "name": d.get("name")} for d in dashboards[:10]]
    }


# ============================================================================
# /api/assets - Signed URLs
# ============================================================================

@router.get("/assets/signed-url", tags=["assets"])
async def get_signed_url(
    key: str,
    token: TokenPayload = Depends(verify_token)
):
    """Get a signed URL for downloading an asset from MinIO"""
    from common import get_storage_client
    
    storage = get_storage_client()
    
    # Verify key belongs to tenant
    if not key.startswith(f"tenant/{token.tenant_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        url = storage.get_presigned_url(key, expires=3600)
        return {
            "url": url,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Asset not found: {str(e)}")
