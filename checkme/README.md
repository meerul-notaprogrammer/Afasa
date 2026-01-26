# AFASA 2.0 - AI Agricultural Monitoring System

## 🌾 Overview
Multi-tenant AI-powered agricultural monitoring platform combining computer vision, IoT sensors, and intelligent automation for crop health analysis and pest detection.

## 🏗️ Architecture
- **Microservices**: 9 specialized services (Vision, IoT, Ops, Reports, etc.)
- **Event-Driven**: NATS JetStream for async communication
- **Multi-Tenant**: Row-level security with Keycloak OIDC
- **Storage**: Postgres + MinIO (S3-compatible)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend)

### Environment Setup
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Run Full Stack
```bash
docker-compose up -d
```

**Services will be available at:**
- Portal: http://localhost (Traefik routes to port 80)
- Keycloak: http://localhost:8080
- Traefik Dashboard: http://localhost:8081
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

## 📁 Project Structure
```
afasa2.0/
├── services/
│   ├── common/            # Shared library (models, auth, events)
│   ├── ops/               # Task & rule engine
│   ├── tb_adapter/        # ThingsBoard & UbiBot integration
│   ├── vision_yolo/       # YOLOv8 object detection
│   ├── vision_reasoner/   # Gemini AI analysis
│   ├── media/             # Snapshot & video management
│   ├── report/            # PDF/CSV generation
│   ├── telegram/          # Telegram notifications
│   ├── portal/            # React frontend
│   └── retention_cleaner/ # Data cleanup worker
├── infra/                 # Infrastructure configs (Postgres, MediaMTX, etc.)
├── docs/                  # Documentation
└── docker-compose.yml     # Full stack orchestration
```

## 🔧 Development

### Local Service Development
```bash
cd services/<service-name>
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd services/portal
npm install
npm run dev
```

## 📚 Documentation
- **[AI Collaboration Brief](AI_COLLABORATION_BRIEF.md)** - For AI assistants working on this project
- **[Problem Statement](problem_statement.md)** - Current issues and fix plan
- **[Architecture Docs](docs/)** - Detailed system design

## 🤝 Contributing
This project uses AI-assisted development. See `AI_COLLABORATION_BRIEF.md` for collaboration guidelines.

## 📄 License
MIT License

## 🔗 Related Projects
- AFASA 1.0 (Legacy monolith - deprecated)
- ThingsBoard Integration
- UbiBot IoT Platform
