# Phase 3: Governance + ThingsBoard Integration

> **Status**: AUTOMATION & DASHBOARDS
> **Prerequisite**: Phase 2 complete (vision core working)
> **Duration**: 1-2 weeks

---

## Objective

Integrate ThingsBoard for device management and dashboards. Implement the rule proposal/approval governance flow.

---

## 1) ThingsBoard Adapter (afasa-tb-adapter)

### 1.1 Device Sync

**Requirements:**
- Sync AFASA devices to ThingsBoard
- Maintain mapping: AFASA device ID ↔ TB device ID
- Bidirectional status updates

**Implementation Tasks:**

1. **TB Client Wrapper**
   ```python
   class ThingsBoardClient:
       def __init__(self, base_url: str, jwt: str):
           self.base_url = base_url
           self.jwt = jwt
       
       async def create_device(self, device: Device) -> str:
           """Create device in TB, return TB device ID"""
           response = await self.post("/api/device", {
               "name": device.name,
               "type": device.type,
               "label": device.label
           })
           return response["id"]["id"]
       
       async def get_device_credentials(self, device_id: str) -> str:
           """Get device access token for telemetry"""
           response = await self.get(f"/api/device/{device_id}/credentials")
           return response["credentialsId"]
   ```

2. **Sync Service**
   ```python
   async def sync_device_to_tb(device: Device):
       # 1. Get TB JWT (decrypt secret_ref)
       # 2. Check if device already synced
       # 3. Create or update in TB
       # 4. Store mapping in database
       # 5. Audit log
   ```

### 1.2 Embed Token Minting

**Requirements:**
- Generate short-lived tokens for dashboard embedding
- Frontend uses these for iframe src

**Implementation Tasks:**

1. **Token Endpoint**
   ```python
   @router.post("/api/tb/embed-token")
   async def get_embed_token(
       dashboard_id: Optional[str] = None,
       tenant: Tenant = Depends(get_tenant)
   ):
       # 1. Get TB admin JWT (from secret_ref)
       # 2. Create public dashboard link or embed token
       # 3. Return URL with token
       return {
           "url": f"{tb_base_url}/dashboard/{dashboard_id}?publicId={public_id}",
           "expires_at": (utc_now() + timedelta(hours=1)).isoformat()
       }
   ```

### 1.3 Dashboard Discovery

**Requirements:**
- List available dashboards for tenant
- Allow selection of default dashboard

**Implementation Tasks:**

1. **Dashboard List Endpoint**
   ```python
   @router.get("/api/integrations/thingsboard/dashboards")
   async def list_dashboards(tenant: Tenant = Depends(get_tenant)):
       tb_client = await get_tb_client(tenant)
       dashboards = await tb_client.get_tenant_dashboards()
       return {"dashboards": dashboards}
   ```

---

## 2) Rule Proposal System

### 2.1 Rule Proposals

**Requirements:**
- AI can propose new rules
- Proposals stored in pending state
- Human approval required before activation

**Implementation Tasks:**

1. **Database Schema**
   ```sql
   CREATE TYPE rule_status AS ENUM ('pending', 'approved', 'rejected', 'active', 'disabled');
   CREATE TYPE rule_origin AS ENUM ('ai', 'user');
   
   CREATE TABLE rule_proposals (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       tenant_id UUID NOT NULL REFERENCES tenants(id),
       origin rule_origin NOT NULL DEFAULT 'ai',
       name VARCHAR(255) NOT NULL,
       trigger_condition JSONB NOT NULL,
       action JSONB NOT NULL,
       target_device_id UUID REFERENCES devices(id),
       safety_classification VARCHAR(50),
       reason TEXT,
       confidence DECIMAL(5,4),
       status rule_status NOT NULL DEFAULT 'pending',
       reviewed_by UUID,
       reviewed_at TIMESTAMPTZ,
       review_reason TEXT,
       tb_rulechain_id VARCHAR(255),
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   ```

2. **AI Proposal Creation**
   ```python
   # In vision_reasoner service
   async def propose_rule(assessment: Assessment):
       if assessment.suggested_rule:
           proposal = RuleProposal(
               tenant_id=assessment.tenant_id,
               origin="ai",
               name=assessment.suggested_rule.name,
               trigger_condition=assessment.suggested_rule.trigger,
               action=assessment.suggested_rule.action,
               safety_classification=classify_safety(assessment.suggested_rule),
               reason=assessment.reasoning,
               confidence=assessment.confidence
           )
           await db.save(proposal)
           await nats.publish("afasa.ops.v1.rule.proposed", proposal.to_event())
   ```

### 2.2 Approval Flow

**Requirements:**
- Portal shows pending proposals
- Approve creates TB rulechain
- Reject leaves system unchanged
- All actions audited

**Implementation Tasks:**

1. **Approval Endpoint**
   ```python
   @router.post("/api/rule-proposals/{id}/approve")
   async def approve_proposal(
       id: UUID,
       request: ApprovalRequest,
       user: User = Depends(get_user)
   ):
       proposal = await db.get(RuleProposal, id)
       
       # 1. Create TB rulechain
       tb_rulechain_id = await tb_adapter.create_rulechain(proposal)
       
       # 2. Update proposal status
       proposal.status = "approved"
       proposal.reviewed_by = user.id
       proposal.reviewed_at = utc_now()
       proposal.review_reason = request.reason
       proposal.tb_rulechain_id = tb_rulechain_id
       
       # 3. Create active rule
       rule = Rule(
           tenant_id=proposal.tenant_id,
           proposal_id=proposal.id,
           name=proposal.name,
           trigger_condition=proposal.trigger_condition,
           action=proposal.action,
           status="active"
       )
       
       # 4. Audit log
       await audit.log(
           action="rule.approved",
           actor_type="user",
           actor_id=str(user.id),
           resource_type="rule_proposal",
           resource_id=proposal.id,
           before_state={"status": "pending"},
           after_state={"status": "approved", "tb_rulechain_id": tb_rulechain_id}
       )
       
       # 5. Publish event
       await nats.publish("afasa.ops.v1.rule.approved", {...})
       
       return {"rule_id": rule.id, "tb_rulechain_id": tb_rulechain_id}
   ```

2. **Rejection Endpoint**
   ```python
   @router.post("/api/rule-proposals/{id}/reject")
   async def reject_proposal(
       id: UUID,
       request: RejectionRequest,
       user: User = Depends(get_user)
   ):
       proposal = await db.get(RuleProposal, id)
       
       # 1. Update status only (no TB changes)
       proposal.status = "rejected"
       proposal.reviewed_by = user.id
       proposal.reviewed_at = utc_now()
       proposal.review_reason = request.reason
       
       # 2. Audit log
       await audit.log(
           action="rule.rejected",
           actor_type="user",
           actor_id=str(user.id),
           resource_type="rule_proposal",
           resource_id=proposal.id,
           reason=request.reason
       )
       
       # 3. Publish event
       await nats.publish("afasa.ops.v1.rule.rejected", {...})
       
       return {"success": True}
   ```

### 2.3 TB Rulechain Creation

**Requirements:**
- Convert AFASA rule to TB rulechain format
- Activate in ThingsBoard
- Handle device protections

**Implementation Tasks:**

1. **Rulechain Builder**
   ```python
   class RulechainBuilder:
       def build(self, proposal: RuleProposal) -> dict:
           """Convert AFASA rule to TB rulechain JSON"""
           return {
               "name": f"AFASA: {proposal.name}",
               "type": "CORE",
               "firstRuleNodeId": None,
               "root": False,
               "debugMode": False,
               "configuration": self._build_nodes(proposal)
           }
       
       def _build_nodes(self, proposal: RuleProposal) -> dict:
           # Convert trigger_condition and action to TB node format
           pass
   ```

2. **Protection Check**
   ```python
   async def check_rule_allowed(proposal: RuleProposal, settings: TenantSettings):
       # Check if target device is protected
       if str(proposal.target_device_id) in settings.protected_devices:
           raise ProtectedDeviceError("Cannot modify protected device")
       
       # Check daily rule change limit
       changes_today = await count_rule_changes_today(proposal.tenant_id)
       if changes_today >= settings.max_daily_rule_changes:
           raise RateLimitError("Daily rule change limit reached")
   ```

---

## 3) Dashboard Template Selection

### Requirements
- Tenant can select default TB dashboard
- Dashboard ID stored in settings
- Used for main dashboard embed

### Implementation Tasks

1. **Settings Update**
   ```python
   @router.post("/api/settings/dashboard")
   async def set_default_dashboard(
       request: SetDashboardRequest,
       tenant: Tenant = Depends(get_tenant)
   ):
       settings = await get_tenant_settings(tenant.id)
       settings.default_dashboard_id = request.dashboard_id
       await db.save(settings)
       return {"success": True}
   ```

---

## Event Flow

```
┌──────────┐     afasa.ops.v1.rule.proposed
│ Reasoner │────────────────────────────────▶
└──────────┘                                 │
                                             ▼
                                      ┌──────────┐
                                      │  Portal  │
                                      │ (pending)│
                                      └────┬─────┘
                                           │
            ┌──────────────────────────────┴──────────────────────────────┐
            │                                                              │
            ▼ approve                                               reject ▼
     ┌──────────┐                                                   ┌──────────┐
     │   Ops    │                                                   │   Ops    │
     └────┬─────┘                                                   └────┬─────┘
          │                                                              │
          ▼                                                              ▼
   ┌──────────┐     afasa.ops.v1.rule.rejected                    ┌──────────┐
   │TB Adapter│◀──────────────────────────────                    │  Audit   │
   └────┬─────┘                                                   └──────────┘
        │
        ▼ create rulechain
   ┌──────────┐
   │ThingsBoard│
   └──────────┘
```

---

## Verification Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 3.1 | TB Adapter syncs devices | ⬜ |
| 3.2 | Embed token minting works | ⬜ |
| 3.3 | TB dashboard lists available | ⬜ |
| 3.4 | Rule proposals stored in database | ⬜ |
| 3.5 | Approval creates TB rulechain | ⬜ |
| 3.6 | Rejection leaves system unchanged | ⬜ |
| 3.7 | All actions audited | ⬜ |
| 3.8 | Protected devices enforced | ⬜ |

**FAIL if:** Rules auto-activate without policy gate / human approval.

---

## Deliverables

1. TB device sync working
2. Embed token minting functional
3. Rule proposal CRUD complete
4. Approval → rulechain activation
5. All governance actions audited

---

## References

- [Master Architecture](../MASTER_ARCHITECTURE.md)
- [User Flows](../USER_FLOWS.md) - Rule Proposal/Approval Flow
- [MVP Acceptance Checklist](../MVP_ACCEPTANCE_CHECKLIST.md) - Phase 3 criteria
