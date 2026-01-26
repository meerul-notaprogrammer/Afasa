INSERT INTO tenants (id, name, created_at) VALUES ('a1b2c3d4-e5f6-7890-1234-567890abcdef', 'Default Tenant', NOW()) ON CONFLICT (id) DO NOTHING;
