# AFASA 2.0 - VPS Deployment Script
# Deploys the robust audit fixes to Ubuntu VPS

$VPS_HOST = "100.88.15.112"
$VPS_PORT = "2222"
$VPS_USER = "meerul"
$BRANCH = "fix/robust-audit-2026-01-26"
$REPO_URL = "https://github.com/meerul-notaprogrammer/Afasa.git"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AFASA 2.0 - VPS Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Target: $VPS_USER@$VPS_HOST:$VPS_PORT" -ForegroundColor Yellow
Write-Host "Branch: $BRANCH" -ForegroundColor Yellow
Write-Host ""

# Create deployment commands
$deployCommands = @"
#!/bin/bash
set -e

echo "========================================="
echo "AFASA 2.0 - Deployment Starting"
echo "========================================="
echo ""

# Navigate to project directory
cd ~/afasa2.0 || {
    echo "Directory ~/afasa2.0 not found. Cloning repository..."
    cd ~
    git clone $REPO_URL afasa2.0
    cd afasa2.0
}

echo "📥 Fetching latest changes from GitHub..."
git fetch origin

echo "🔄 Checking out branch: $BRANCH"
git checkout $BRANCH
git pull origin $BRANCH

echo ""
echo "✅ Code updated successfully!"
echo ""

# Check if Docker is running
echo "🐳 Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Show current containers
echo "📊 Current container status:"
docker compose ps
echo ""

# Ask about database reset
echo "⚠️  DATABASE MIGRATION REQUIRED"
echo ""
echo "The 'devices' table needs to be created. Choose an option:"
echo "1) Fresh start - Delete pgdata volume and recreate (TESTING ONLY)"
echo "2) Manual migration - I'll provide SQL commands (PRODUCTION)"
echo "3) Skip - Database already migrated"
echo ""
read -p "Enter choice (1/2/3): " db_choice

case \$db_choice in
    1)
        echo "🗑️  Removing pgdata volume..."
        docker compose down
        docker volume rm afasa20_pgdata 2>/dev/null || true
        echo "✅ Volume removed. Will be recreated on startup."
        ;;
    2)
        echo ""
        echo "📝 Run these SQL commands manually:"
        echo ""
        echo "docker exec -it \$(docker compose ps -q postgres) psql -U afasa -d afasa"
        echo ""
        cat << 'EOSQL'
CREATE TABLE IF NOT EXISTS devices (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  provider text NOT NULL,
  external_id text NOT NULL,
  name text NOT NULL,
  device_type text,
  location text,
  enabled boolean NOT NULL DEFAULT true,
  last_seen timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider, external_id)
);

CREATE INDEX IF NOT EXISTS devices_tenant_idx ON devices(tenant_id);
CREATE INDEX IF NOT EXISTS devices_provider_idx ON devices(provider);

ALTER TABLE devices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_devices ON devices
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EOSQL
        echo ""
        read -p "Press Enter after running the SQL commands..."
        ;;
    3)
        echo "⏭️  Skipping database migration"
        ;;
esac

echo ""
echo "🔨 Building and starting services..."
docker compose pull
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "🔍 Checking Traefik logs for errors..."
docker compose logs --tail=50 traefik | grep -i "error\|version" || echo "✅ No errors found"

echo ""
echo "🏥 Health Checks:"
echo "=================================="

# Function to check endpoint
check_endpoint() {
    local name=\$1
    local url=\$2
    echo -n "Checking \$name... "
    if curl -f -s -o /dev/null \$url; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
}

check_endpoint "Traefik Dashboard" "http://localhost:8081/dashboard/"
check_endpoint "Ops Service" "http://localhost/api/ops/readyz"
check_endpoint "TB Adapter" "http://localhost/api/tb/readyz"
check_endpoint "Report Service" "http://localhost/api/report/readyz"
check_endpoint "Media Service" "http://localhost/api/media/readyz"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "📝 Next Steps:"
echo "1. Check logs: docker compose logs -f [service-name]"
echo "2. Test UbiBot sync: curl -X POST http://localhost/api/discovery/ubibot/sync"
echo "3. View Traefik dashboard: http://localhost:8081"
echo ""
"@

# Save deployment script to temp file
$tempScript = [System.IO.Path]::GetTempFileName() + ".sh"
$deployCommands | Out-File -FilePath $tempScript -Encoding ASCII -NoNewline

Write-Host "🚀 Connecting to VPS and deploying..." -ForegroundColor Green
Write-Host ""

# Execute deployment via SSH
ssh -p $VPS_PORT "$VPS_USER@$VPS_HOST" "bash -s" < $tempScript

# Cleanup
Remove-Item $tempScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment script completed!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
