"""
AFASA 2.0 - ThingsBoard Adapter Service
Integration with ThingsBoard and UbiBot
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
from app.routes_extended import router as extended_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_bus = await get_event_bus()
    yield
    await event_bus.disconnect()


app = FastAPI(
    title="AFASA TB Adapter Service",
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

app.include_router(router, prefix="/api/tb")
app.include_router(extended_router, prefix="/api")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "afasa-tb-adapter"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "service": "afasa-tb-adapter"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

