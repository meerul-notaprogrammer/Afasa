"""
AFASA 2.0 - Ops Service
Scheduling, task management, and policy gate
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus

from app.routes import router
from app.routes_extended import router as extended_router
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus()
    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()
    await event_bus.disconnect()


app = FastAPI(
    title="AFASA Ops Service",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/ops")
app.include_router(extended_router, prefix="/api")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "afasa-ops"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "service": "afasa-ops"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

