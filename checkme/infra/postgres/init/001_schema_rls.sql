CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Users (optional; use if you want local profile + telegram link)
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email text,
  display_name text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Tenant settings (AI governance)
CREATE TABLE IF NOT EXISTS tenant_settings (
  tenant_id uuid PRIMARY KEY REFERENCES tenants(id),
  ai_rule_creation text NOT NULL DEFAULT 'suggest_only',     -- suggest_only|allow
  ai_auto_activation boolean NOT NULL DEFAULT false,
  max_daily_rule_changes int NOT NULL DEFAULT 3,
  protected_devices jsonb NOT NULL DEFAULT '[]'::jsonb,
  protected_rules jsonb NOT NULL DEFAULT '[]'::jsonb,
  retention_snapshots_days int NOT NULL DEFAULT 30,
  retention_annotated_days int NOT NULL DEFAULT 90,
  retention_reports_days int NOT NULL DEFAULT 90,
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Cameras
CREATE TABLE IF NOT EXISTS cameras (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name text NOT NULL,
  location text,
  rtsp_url text NOT NULL,
  onvif_enabled boolean NOT NULL DEFAULT false,
  onvif_host text,
  onvif_port int,
  onvif_username text,
  onvif_password_ref text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cameras_tenant_idx ON cameras(tenant_id);

-- Snapshots
CREATE TABLE IF NOT EXISTS snapshots (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  camera_id uuid NOT NULL REFERENCES cameras(id),
  s3_key text NOT NULL,
  taken_at timestamptz NOT NULL,
  reason text NOT NULL,
  width int,
  height int,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS snapshots_tenant_time_idx ON snapshots(tenant_id, taken_at DESC);

-- Detections
CREATE TABLE IF NOT EXISTS detections (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  snapshot_id uuid NOT NULL REFERENCES snapshots(id),
  camera_id uuid NOT NULL REFERENCES cameras(id),
  label text NOT NULL,
  confidence real NOT NULL,
  bbox jsonb NOT NULL,
  model text NOT NULL,
  annotated_s3_key text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS detections_tenant_camera_time_idx ON detections(tenant_id, camera_id, created_at DESC);
CREATE INDEX IF NOT EXISTS detections_label_idx ON detections(label);

-- Assessments (Gemini reasoning)
CREATE TABLE IF NOT EXISTS assessments (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  snapshot_id uuid NOT NULL REFERENCES snapshots(id),
  camera_id uuid NOT NULL REFERENCES cameras(id),
  severity text NOT NULL,
  hypotheses jsonb NOT NULL,
  recommended_actions jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS assessments_tenant_time_idx ON assessments(tenant_id, created_at DESC);

-- Tasks (daily/weekly)
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  title text NOT NULL,
  description text,
  priority int NOT NULL DEFAULT 3,
  status text NOT NULL DEFAULT 'open',   -- open|done|dismissed
  source text NOT NULL DEFAULT 'ai',     -- ai|user|system
  due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS tasks_tenant_due_idx ON tasks(tenant_id, due_at DESC);

-- Rule proposals (AI intent => TB rule chain)
CREATE TABLE IF NOT EXISTS rule_proposals (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  intent_type text NOT NULL,
  proposed_rule jsonb NOT NULL,
  confidence real NOT NULL,
  requires_approval boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|activated
  tb_rule_id text,
  created_by text NOT NULL DEFAULT 'ai',   -- ai|user
  created_at timestamptz NOT NULL DEFAULT now(),
  approved_at timestamptz
);
CREATE INDEX IF NOT EXISTS rule_proposals_tenant_status_idx ON rule_proposals(tenant_id, status);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  format text NOT NULL,                  -- pdf|xlsx
  range_from timestamptz NOT NULL,
  range_to timestamptz NOT NULL,
  s3_key text,
  status text NOT NULL DEFAULT 'queued', -- queued|ready|failed
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS reports_tenant_time_idx ON reports(tenant_id, created_at DESC);

-- Telegram links
CREATE TABLE IF NOT EXISTS telegram_links (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid,
  chat_id text NOT NULL,
  linked_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, chat_id)
);

-- Secrets Table
CREATE TABLE IF NOT EXISTS secrets (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  purpose text NOT NULL,                 -- rtsp_password, onvif_password, ubibot_key, etc.
  cipher_text bytea NOT NULL,
  key_version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS secrets_tenant_idx ON secrets(tenant_id);

-- Audit Log (Append-only)
CREATE TABLE IF NOT EXISTS audit_log (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  actor_type text NOT NULL,          -- user|ai|system
  actor_id text,                     -- user sub or service name
  action text NOT NULL,              -- rule_proposed|rule_approved|etc.
  target_type text NOT NULL,         -- rule_proposal|tb_rule|device|camera|settings
  target_id text NOT NULL,
  reason text,                       -- AI explanation or human note
  confidence real,                   -- for AI actions
  before jsonb,                      -- previous state
  after jsonb,                       -- new state
  occurred_at timestamptz NOT NULL DEFAULT now(),
  correlation_id uuid
);
CREATE INDEX IF NOT EXISTS audit_tenant_time_idx ON audit_log(tenant_id, occurred_at DESC);

-- ========== RLS ==========
-- Convention: API sets "SET app.tenant_id = '<uuid>'" per request, per connection.

ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rule_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Helper: protect against missing tenant id
CREATE POLICY tenant_isolation_cameras ON cameras
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_snapshots ON snapshots
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_detections ON detections
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_assessments ON assessments
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_tasks ON tasks
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_rule_proposals ON rule_proposals
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_reports ON reports
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_telegram_links ON telegram_links
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_users ON users
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_tenant_settings ON tenant_settings
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_secrets ON secrets
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);

CREATE POLICY tenant_isolation_audit ON audit_log
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
