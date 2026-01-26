-- Initialize AFASA 2.0 Database
-- Create first tenant and admin user

INSERT INTO tenants (id, name, contact_email, tier)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Main Farm',
    'admin@farm.local',
    'standard'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tenant_settings (tenant_id, retention_snapshots_days, retention_reports_days, ai_rule_creation, ai_auto_activation, max_daily_rule_changes, protected_devices, alert_cooldown_sec)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    30,
    90,
    'suggest_only',
    false,
    3,
    '{}',
    3600
) ON CONFLICT (tenant_id) DO NOTHING;

-- Success message
SELECT 'AFASA 2.0 initialized successfully!' as message;
