
# AFASA 2.0 - Remote Deployment Script
# Usage: ./deploy_to_vps.ps1

$VPS_USER = "meerul"
$VPS_IP = "192.168.1.110"
$VPS_PORT = "2222"
$REMOTE_DIR = "~/afasa2.0"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   AFASA 2.0 - REMOTE DEPLOYMENT" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Clean up local artifacts (optional, to save bandwidth)
# Write-Host "Cleaning local build artifacts..."
# Remove-Item -Path ".\services\*\__pycache__" -Recurse -ErrorAction SilentlyContinue

# 2. Create Remote Directory
Write-Host "`n[1/5] Creating remote directory ($REMOTE_DIR)..."
ssh -p $VPS_PORT $VPS_USER@$VPS_IP "mkdir -p $REMOTE_DIR"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to connect or create directory."; exit }

# 3. Transfer Files
Write-Host "`n[2/5] Transferring project files (this may take a minute)..."
# We exclude .git, node_modules, and venv to speed up transfer
scp -P $VPS_PORT -r ./* $VPS_USER@$VPS_IP":"$REMOTE_DIR
if ($LASTEXITCODE -ne 0) { Write-Error "File transfer failed."; exit }

# 4. Set Permissions & Setup Environment
Write-Host "`n[3/5] Setting up remote environment..."
$SETUP_CMD = "
    cd $REMOTE_DIR && \
    chmod +x deploy.sh && \
    if [ ! -f .env ]; then cp .env.example .env; fi
"
ssh -p $VPS_PORT $VPS_USER@$VPS_IP $SETUP_CMD

# 5. Execute Remote Deployment
Write-Host "`n[4/5] Executing Remote Deployment (Docker Build & Up)..."
Write-Host "Check the VPS logs if this step takes a long time." -ForegroundColor Yellow
ssh -p $VPS_PORT $VPS_USER@$VPS_IP "cd $REMOTE_DIR && ./deploy.sh"

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "   DEPLOYMENT INITIATED SUCCESSFULLY" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
