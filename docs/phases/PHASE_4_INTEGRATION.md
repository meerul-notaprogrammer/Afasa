# Phase 4: Integration & Messaging

> **Status**: NOTIFICATIONS & INTEGRATIONS
> **Prerequisite**: Phase 3 complete (governance working)
> **Duration**: 1 week

---

## Objective

Complete all external integrations: Telegram bot, UbiBot sync, and ensure all messaging flows work correctly.

---

## 1) Telegram Integration (afasa-telegram)

### 1.1 Bot Setup

**Requirements:**
- Webhook-based bot (not polling)
- Commands: `/start`, `/status`, `/report`
- Secure webhook with secret

**Implementation Tasks:**

1. **Webhook Registration**
   ```python
   async def register_webhook():
       webhook_url = f"{PUBLIC_BASE_URL}/api/telegram/webhook"
       await telegram_api.set_webhook(
           url=webhook_url,
           secret_token=TELEGRAM_WEBHOOK_SECRET
       )
   ```

2. **Webhook Handler**
   ```python
   @router.post("/api/telegram/webhook")
   async def telegram_webhook(
       request: Request,
       x_telegram_bot_api_secret_token: str = Header(None)
   ):
       # Verify secret
       if x_telegram_bot_api_secret_token != TELEGRAM_WEBHOOK_SECRET:
           raise HTTPException(403, "Invalid secret")
       
       update = await request.json()
       await process_telegram_update(update)
       return {"ok": True}
   ```

### 1.2 Command Handlers

**Implementation Tasks:**

1. **Start Command** (link bot to tenant)
   ```python
   async def handle_start(message: dict):
       chat_id = message["chat"]["id"]
       # Extract tenant linking token from deep link
       # e.g., /start link_abc123
       args = message.get("text", "").split()
       if len(args) > 1:
           link_token = args[1]
           tenant_id = await validate_link_token(link_token)
           await store_telegram_link(tenant_id, chat_id)
           await send_message(chat_id, "✅ Successfully linked to your farm!")
   ```

2. **Status Command**
   ```python
   async def handle_status(message: dict):
       chat_id = message["chat"]["id"]
       tenant_id = await get_tenant_by_chat(chat_id)
       
       status = await get_farm_status(tenant_id)
       await send_message(chat_id, format_status_message(status))
   ```

3. **Report Command**
   ```python
   async def handle_report(message: dict):
       chat_id = message["chat"]["id"]
       tenant_id = await get_tenant_by_chat(chat_id)
       
       # Trigger report generation
       job_id = await request_report(tenant_id, "daily", "pdf")
       await send_message(chat_id, "📊 Generating report... I'll send it when ready.")
   ```

### 1.3 Notification Types

| Type | Trigger | Message |
|------|---------|---------|
| Task Created | New high-priority task | 🌱 New task: ... |
| Assessment | Critical severity | ⚠️ Alert: ... |
| Rule Proposed | AI proposes rule | 🤖 AI suggests: ... |
| Device Offline | Health check fails | 📷 Camera offline: ... |
| Report Ready | Report generated | 📊 Report ready: ... |

### 1.4 Linking Flow

**Portal → Telegram:**
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Portal  │────▶│   API    │────▶│ Telegram │
│(Settings)│     │ (token)  │     │   Bot    │
└──────────┘     └──────────┘     └──────────┘
     │                                 │
     │ User clicks "Link Telegram"     │
     ▼                                 │
┌──────────┐                          │
│  Shows   │                          │
│QR / Link │◀─────────────────────────┘
│t.me/bot? │       /start link_{token}
│start=... │
└──────────┘
```

---

## 2) UbiBot Integration

### 2.1 API Connection

**Requirements:**
- Store API key securely (secret_ref)
- Sync devices on demand
- Periodic telemetry fetch

**Implementation Tasks:**

1. **UbiBot Client**
   ```python
   class UbiBotClient:
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.base_url = "https://api.ubibot.io"
       
       async def list_devices(self) -> list[dict]:
           response = await self.get("/channels")
           return response["channels"]
       
       async def get_latest_data(self, channel_id: str) -> dict:
           response = await self.get(f"/channels/{channel_id}/feeds/last")
           return response
   ```

2. **Sync Endpoint**
   ```python
   @router.post("/api/discovery/ubibot/sync")
   async def sync_ubibot_devices(tenant: Tenant = Depends(get_tenant)):
       # 1. Get API key from secrets
       api_key = await secrets.get(tenant.id, "ubibot_api_key")
       
       # 2. Fetch devices from UbiBot
       client = UbiBotClient(api_key)
       ubibot_devices = await client.list_devices()
       
       # 3. Create/update in device registry
       created = 0
       for ub_device in ubibot_devices:
           device = await create_or_update_device(
               tenant_id=tenant.id,
               type="iot",
               subtype="ubibot",
               external_id=ub_device["channel_id"],
               name=ub_device["name"],
               metadata=ub_device
           )
           created += 1
       
       # 4. Optionally sync to ThingsBoard
       # 5. Audit log
       
       return {"devices_found": len(ubibot_devices), "devices_created": created}
   ```

### 2.2 Telemetry Ingestion

**Implementation Tasks:**

1. **Scheduled Telemetry Fetch**
   ```python
   @scheduler.interval(minutes=5)
   async def fetch_ubibot_telemetry():
       for tenant in await get_active_tenants():
           api_key = await secrets.get(tenant.id, "ubibot_api_key")
           if not api_key:
               continue
           
           client = UbiBotClient(api_key)
           devices = await get_ubibot_devices(tenant.id)
           
           for device in devices:
               data = await client.get_latest_data(device.external_id)
               await store_telemetry(device.id, data)
               # Forward to ThingsBoard if synced
   ```

---

## 3) Report Delivery

### 3.1 Report Service Integration

**Requirements:**
- Notify when report is ready
- Provide download link via Telegram
- Signed URL expires after short period

**Implementation Tasks:**

1. **Report Ready Handler**
   ```python
   @nats.subscribe("afasa.report.v1.ready")
   async def on_report_ready(event):
       tenant_id = event["tenant_id"]
       report_id = event["report_id"]
       
       # Get Telegram chat for tenant
       chat_id = await get_telegram_chat(tenant_id)
       if not chat_id:
           return
       
       # Generate signed URL
       signed_url = await minio.presign_get(
           key=event["minio_key"],
           expires=timedelta(hours=24)
       )
       
       # Send notification
       await send_message(chat_id, f"""
   📊 *Your report is ready!*
   
   {event["report_type"].title()} Report
   Generated: {event["timestamp"]}
   
   [Download Report]({signed_url})
   
   _Link expires in 24 hours_
   """)
   ```

---

## 4) Alert Routing

### 4.1 Alert Manager

**Requirements:**
- Route alerts to appropriate channels
- Respect per-channel rate limits
- Log all routing decisions

**Implementation Tasks:**

1. **Alert Router**
   ```python
   class AlertRouter:
       async def route(self, alert: Alert, tenant_settings: TenantSettings):
           channels = []
           
           # Telegram
           if tenant_settings.telegram_enabled:
               channels.append(TelegramChannel(tenant_settings.telegram_chat_id))
           
           # Future: Email, WhatsApp, etc.
           
           for channel in channels:
               allowed, reason = await self.rate_limiter.should_send(
                   tenant_id=alert.tenant_id,
                   channel=channel.name,
                   alert_type=alert.type
               )
               
               if allowed:
                   await channel.send(alert)
                   await self.audit.log(action="alert.sent", channel=channel.name)
               else:
                   await self.audit.log(
                       action="alert.skipped",
                       channel=channel.name,
                       reason=reason
                   )
   ```

---

## Verification Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 4.1 | Telegram webhook works | ⬜ |
| 4.2 | /start links to tenant | ⬜ |
| 4.3 | /status returns farm status | ⬜ |
| 4.4 | /report triggers generation | ⬜ |
| 4.5 | Notifications respect rate limits | ⬜ |
| 4.6 | UbiBot connect stores key | ⬜ |
| 4.7 | UbiBot sync populates devices | ⬜ |
| 4.8 | Report download link works | ⬜ |

---

## Deliverables

1. Telegram bot fully functional
2. UbiBot integration complete
3. Report delivery via Telegram
4. All alerts routed correctly

---

## References

- [User Flows](../USER_FLOWS.md) - Incident Flow
- [Operational Hardening](../OPERATIONAL_HARDENING.md) - Rate Limiting (E)
