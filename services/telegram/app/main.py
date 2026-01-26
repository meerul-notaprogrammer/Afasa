"""
AFASA 2.0 - Telegram Bot Service
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus

from app.routes import router
from app.subscriber import start_notification_subscriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus()
    await start_notification_subscriber()
    yield
    # Shutdown
    await event_bus.disconnect()


app = FastAPI(
    title="AFASA Telegram Service",
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

app.include_router(router, prefix="/api/telegram")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "afasa-telegram"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "service": "afasa-telegram"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

