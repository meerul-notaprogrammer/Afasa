"""
AFASA 2.0 - Media Service
Camera management and snapshot capture
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import sys
sys.path.insert(0, '/app/services')

from common import get_event_bus, verify_token, TokenPayload

from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    event_bus = await get_event_bus()
    yield
    # Shutdown
    await event_bus.disconnect()


app = FastAPI(
    title="AFASA Media Service",
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

app.include_router(router, prefix="/api/media")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "afasa-media"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "service": "afasa-media"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

