"""
AFASA 2.0 - TB Adapter Routes
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
sys.path.insert(0, '/app/services')

from common import verify_token, require_role, TokenPayload
from app.tb_api import get_tb_client
from app.ubibot import import_ubibot_to_tb

router = APIRouter(tags=["tb-adapter"])


class UbiBotImportRequest(BaseModel):
    ubibot_api_key: str


class UbiBotImportResponse(BaseModel):
    imported: int
    devices: List[Dict[str, Any]]


class AlarmCreateRequest(BaseModel):
    tb_device_id: str
    type: str
    severity: str  # CRITICAL, MAJOR, MINOR, WARNING, INDETERMINATE
    details: Optional[Dict[str, Any]] = None


class AlarmCreateResponse(BaseModel):
    ok: bool
    tb_alarm_id: str


class RuleCreateRequest(BaseModel):
    proposal: Dict[str, Any]


class RuleCreateResponse(BaseModel):
    tb_rule_id: str


@router.get("/devices")
async def list_devices(token: TokenPayload = Depends(verify_token)):
    """List ThingsBoard devices"""
    tb = get_tb_client()
    devices = await tb.get_devices()
    return {"devices": devices}


@router.post("/devices/import/ubibot", response_model=UbiBotImportResponse)
async def import_ubibot(
    body: UbiBotImportRequest,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Import UbiBot channels as ThingsBoard devices"""
    tb = get_tb_client()
    
    try:
        imported = await import_ubibot_to_tb(body.ubibot_api_key, tb)
        return UbiBotImportResponse(
            imported=len(imported),
            devices=imported
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/alarms/create", response_model=AlarmCreateResponse)
async def create_alarm(
    body: AlarmCreateRequest,
    token: TokenPayload = Depends(verify_token)
):
    """Create a ThingsBoard alarm"""
    tb = get_tb_client()
    
    try:
        alarm = await tb.create_alarm(
            body.tb_device_id,
            body.type,
            body.severity,
            body.details
        )
        return AlarmCreateResponse(
            ok=True,
            tb_alarm_id=alarm["id"]["id"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rules/create_from_proposal", response_model=RuleCreateResponse)
async def create_rule_from_proposal(
    body: RuleCreateRequest,
    token: TokenPayload = Depends(require_role("tenant_admin"))
):
    """Create a ThingsBoard rule chain from AFASA proposal"""
    tb = get_tb_client()
    proposal = body.proposal
    
    # Parse proposal into TB rule chain format
    name = proposal.get("name", "AFASA Rule")
    condition = proposal.get("condition", {})
    action = proposal.get("action", {})
    
    # Build simple rule chain nodes
    nodes = [
        {
            "type": "org.thingsboard.rule.engine.filter.TbMsgTypeSwitchNode",
            "name": "Message Type Switch",
            "configuration": {}
        },
        {
            "type": "org.thingsboard.rule.engine.filter.TbJsSwitchNode",
            "name": "Condition Check",
            "configuration": {
                "jsScript": f"""
                    var value = msg['{condition.get("metric", "temperature")}'];
                    var threshold = {condition.get("value", 30)};
                    var op = '{condition.get("op", ">")}';
                    
                    if (op === '>') return value > threshold;
                    if (op === '<') return value < threshold;
                    if (op === '>=') return value >= threshold;
                    if (op === '<=') return value <= threshold;
                    return value === threshold;
                """
            }
        },
        {
            "type": "org.thingsboard.rule.engine.action.TbCreateAlarmNode",
            "name": "Create Alarm",
            "configuration": {
                "alarmType": action.get("type", "AFASA_ALERT"),
                "severity": "MAJOR"
            }
        }
    ]
    
    connections = [
        {"fromIndex": 0, "toIndex": 1, "type": "Post telemetry"},
        {"fromIndex": 1, "toIndex": 2, "type": "True"}
    ]
    
    try:
        rule_chain = await tb.create_rule_chain(name, nodes, connections)
        return RuleCreateResponse(tb_rule_id=rule_chain["id"]["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
