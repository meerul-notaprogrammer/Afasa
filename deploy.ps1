# AFASA 2.0 - Deployment Script for Windows (PowerShell)

Write-Host "==========================================" -ForegroundColor Green
Write-Host "AFASA 2.0 - Deployment Script" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it."
    exit 1
}

Write-Host ""
Write-Host "Step 1: Starting Infrastructure..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
docker compose up -d postgres redis nats minio keycloak traefik mediamtx

Write-Host ""
Write-Host "Waiting for services to be healthy (60s)..."
Start-Sleep -Seconds 60

Write-Host ""
Write-Host "Step 2: Starting Observability Stack..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
docker compose up -d prometheus grafana

Write-Host ""
Write-Host "Step 3: Building AFASA Services..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
docker compose build `
    afasa-media `
    afasa-vision-yolo `
    afasa-vision-reasoner `
    afasa-ops `
    afasa-telegram `
    afasa-report `
    afasa-tb-adapter `
    afasa-retention-cleaner `
    afasa-portal

Write-Host ""
Write-Host "Step 4: Starting AFASA Services..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow
docker compose up -d `
    afasa-media `
    afasa-vision-yolo `
    afasa-vision-reasoner `
    afasa-ops `
    afasa-telegram `
    afasa-report `
    afasa-tb-adapter `
    afasa-retention-cleaner `
    afasa-portal

Write-Host ""
Write-Host "Step 5: Verifying Deployment..." -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Yellow

# Wait for services to start
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "Service Health Checks:" -ForegroundColor Cyan
Write-Host "----------------------"

function Test-Service($name, $url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ ${name}: OK" -ForegroundColor Green
        } else {
            Write-Host "❌ ${name}: FAILED" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ ${name}: FAILED" -ForegroundColor Red
    }
}

Test-Service "Keycloak" "http://localhost:8080/health/ready"
Test-Service "Traefik" "http://localhost:8081/api/overview"
Test-Service "MinIO" "http://localhost:9000/minio/health/live"
Test-Service "NATS" "http://localhost:8222/healthz"
Test-Service "Prometheus" "http://localhost:9090/-/healthy"
Test-Service "Grafana" "http://localhost:3001/api/health"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "  - Portal:     http://localhost/portal/"
Write-Host "  - Keycloak:   http://localhost:8080"
Write-Host "  - Traefik:    http://localhost:8081"
Write-Host "  - MinIO:      http://localhost:9001"
Write-Host "  - Prometheus: http://localhost:9090"
Write-Host "  - Grafana:    http://localhost:3001"
Write-Host ""
