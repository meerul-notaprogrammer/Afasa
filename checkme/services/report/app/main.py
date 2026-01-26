"""
AFASA 2.0 - Report Service
PDF and Excel report generation
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
from app.subscriber import start_report_subscriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    event_bus = await get_event_bus()
    await start_report_subscriber()
    yield
    await event_bus.disconnect()


app = FastAPI(
    title="AFASA Report Service",
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

app.include_router(router, prefix="/api/report")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "afasa-report"}


@app.get("/readyz")
async def readyz():
    return {"status": "ready", "service": "afasa-report"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

