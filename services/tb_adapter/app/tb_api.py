"""
AFASA 2.0 - ThingsBoard API Client
"""
import httpx
from typing import Optional, Dict, Any, List
import sys
sys.path.insert(0, '/app/services')

from common import get_settings

settings = get_settings()


class ThingsBoardClient:
    def __init__(self):
        self._base_url = settings.tb_base_url.rstrip("/")
        self._jwt = settings.tb_jwt
    
    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._jwt}",
            "Content-Type": "application/json"
        }
    
    async def get_devices(self, page: int = 0, page_size: int = 100) -> List[Dict[str, Any]]:
        """Get all devices"""
        if not self._base_url:
            return []
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/api/tenant/devices",
                headers=self._headers,
                params={"page": page, "pageSize": page_size},
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
    
    async def create_device(self, name: str, type: str = "default") -> Dict[str, Any]:
        """Create a new device"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/device",
                headers=self._headers,
                json={"name": name, "type": type},
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
    
    async def post_telemetry(
        self,
        device_id: str,
        telemetry: Dict[str, Any],
        scope: str = "LATEST_TELEMETRY"
    ) -> bool:
        """Post telemetry to a device"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/plugins/telemetry/DEVICE/{device_id}/timeseries/{scope}",
                headers=self._headers,
                json=telemetry,
                timeout=30.0
            )
            return resp.status_code == 200
    
    async def create_alarm(
        self,
        device_id: str,
        alarm_type: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an alarm"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/api/alarm",
                headers=self._headers,
                json={
                    "originator": {"entityType": "DEVICE", "id": device_id},
                    "type": alarm_type,
                    "severity": severity,
                    "status": "ACTIVE_UNACK",
                    "details": details or {}
                },
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
    
    async def create_rule_chain(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a rule chain"""
        async with httpx.AsyncClient() as client:
            # Create rule chain
            resp = await client.post(
                f"{self._base_url}/api/ruleChain",
                headers=self._headers,
                json={"name": name, "type": "CORE"},
                timeout=30.0
            )
            resp.raise_for_status()
            rule_chain = resp.json()
            
            # Add nodes and connections
            rule_chain_id = rule_chain["id"]["id"]
            
            metadata = {
                "firstNodeIndex": 0,
                "nodes": nodes,
                "connections": connections
            }
            
            resp = await client.post(
                f"{self._base_url}/api/ruleChain/{rule_chain_id}/metadata",
                headers=self._headers,
                json=metadata,
                timeout=30.0
            )
            resp.raise_for_status()
            
            return rule_chain


_tb_client: ThingsBoardClient = None


def get_tb_client() -> ThingsBoardClient:
    global _tb_client
    if _tb_client is None:
        _tb_client = ThingsBoardClient()
    return _tb_client
