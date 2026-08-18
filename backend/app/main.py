import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.evidence import router as evidence_router
from app.api.governance import router as governance_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.monitoring import router as monitoring_router
from app.api.observability import router as observability_router
from app.api.passports import public_router
from app.api.passports import router as passports_router
from app.api.semantic_incidents import router as semantic_incidents_router
from app.api.semantic_metrics import router as semantic_metrics_router
from app.api.semantic_registry import router as semantic_registry_router
from app.api.semantic_signals import router as semantic_signals_router
from app.api.sparql import router as sparql_router
from app.api.validation import router as validation_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import observe

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("application_started")
    yield
    logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - started
    route = getattr(request.scope.get("route"), "path", "unmatched")
    observe(request.method, route, response.status_code, duration)
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "no-referrer"
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        },
    )
    return response


app.include_router(health_router)
app.include_router(monitoring_router)
app.include_router(validation_router)
app.include_router(ingestion_router)
app.include_router(observability_router)
app.include_router(governance_router)
app.include_router(dashboard_router)
app.include_router(semantic_registry_router)
app.include_router(semantic_metrics_router)
app.include_router(semantic_incidents_router)
app.include_router(evidence_router)
app.include_router(semantic_signals_router)
app.include_router(sparql_router)
app.include_router(passports_router)
app.include_router(public_router)
