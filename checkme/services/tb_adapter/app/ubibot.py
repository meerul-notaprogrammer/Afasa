"""
AFASA 2.0 - UbiBot Integration
Fetch sensor data from UbiBot cloud
"""
import httpx
from typing import Optional, Dict, Any, List
import sys
sys.path.insert(0, '/app/services')

from common import get_settings

settings = get_settings()

UBIBOT_BASE = "https://api.ubibot.com"


class UbiBotClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        """Get all UbiBot channels (devices)"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UBIBOT_BASE}/channels",
                params={"account_key": self._api_key},
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("channels", [])
    
    async def get_channel_data(self, channel_id: str) -> Dict[str, Any]:
        """Get latest data from a channel"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UBIBOT_BASE}/channels/{channel_id}",
                params={"account_key": self._api_key},
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
    
    async def get_sensors(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get sensors attached to a channel.
        Includes RS485 probes as sensors with prefix 'field'.
        """
        data = await self.get_channel_data(channel_id)
        sensors = []
        
        # Standard fields
        for key in ["field1", "field2", "field3", "field4", "field5", "field6", "field7", "field8", "field9", "field10"]:
            if key in data.get("last_values", {}):
                value_data = data["last_values"][key]
                sensors.append({
                    "field": key,
                    "value": value_data.get("value"),
                    "created_at": value_data.get("created_at"),
                    "is_rs485": key in ["field5", "field6", "field7", "field8"]  # RS485 typically on higher fields
                })
        
        return sensors


async def import_ubibot_to_tb(api_key: str, tb_client) -> List[Dict[str, Any]]:
    """
    Import UbiBot channels as ThingsBoard devices.
    Returns list of imported devices.
    """
    ubibot = UbiBotClient(api_key)
    channels = await ubibot.get_channels()
    
    imported = []
    
    for channel in channels:
        name = channel.get("name", f"UbiBot_{channel['channel_id']}")
        
        # Create device in ThingsBoard
        device = await tb_client.create_device(name, type="ubibot")
        
        # Get latest sensor data
        sensors = await ubibot.get_sensors(channel["channel_id"])
        
        # Post as telemetry
        telemetry = {}
        for sensor in sensors:
            field = sensor["field"]
            value = sensor.get("value")
            if value is not None:
                telemetry[field] = value
        
        if telemetry:
            await tb_client.post_telemetry(device["id"]["id"], telemetry)
        
        imported.append({
            "tb_device_id": device["id"]["id"],
            "name": name,
            "ubibot_channel_id": channel["channel_id"],
            "sensors": len(sensors)
        })
    
    return imported


async def get_ubibot_channels(api_key: str) -> List[Dict[str, Any]]:
    """Helper to get channels with just an API key"""
    client = UbiBotClient(api_key)
    return await client.get_channels()
