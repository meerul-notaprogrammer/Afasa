"""
AFASA 2.0 - Health Check Endpoints
Observability for all services
"""
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

router = APIRouter(tags=["health"])

# Prometheus metrics
REQUEST_COUNT = Counter(
    "afasa_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "afasa_request_latency_seconds",
    "HTTP request latency",
    ["service", "endpoint"]
)


def create_health_router(service_name: str, check_db: callable = None, check_redis: callable = None):
    """Create health check router for a service"""
    health_router = APIRouter(tags=["health"])
    
    @health_router.get("/healthz")
    async def liveness():
        """Kubernetes liveness probe - is the service running?"""
        return {"status": "ok", "service": service_name}
    
    @health_router.get("/readyz")
    async def readiness():
        """Kubernetes readiness probe - is the service ready to accept traffic?"""
        checks = {"service": service_name}
        ready = True
        
        if check_db:
            try:
                await check_db()
                checks["database"] = "connected"
            except Exception as e:
                checks["database"] = f"error: {str(e)}"
                ready = False
        
        if check_redis:
            try:
                await check_redis()
                checks["redis"] = "connected"
            except Exception as e:
                checks["redis"] = f"error: {str(e)}"
                ready = False
        
        status_code = 200 if ready else 503
        return Response(
            content=str({"status": "ready" if ready else "not_ready", **checks}),
            status_code=status_code,
            media_type="application/json"
        )
    
    @health_router.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    return health_router


class RequestTimer:
    """Context manager for timing requests"""
    
    def __init__(self, service: str, endpoint: str):
        self.service = service
        self.endpoint = endpoint
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        REQUEST_LATENCY.labels(
            service=self.service,
            endpoint=self.endpoint
        ).observe(duration)


def record_request(service: str, method: str, endpoint: str, status: int):
    """Record a request for metrics"""
    REQUEST_COUNT.labels(
        service=service,
        method=method,
        endpoint=endpoint,
        status=str(status)
    ).inc()
