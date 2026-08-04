from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "ready"]
    service: str
    environment: str | None = None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=get_settings().app_name)


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ready",
        service=settings.app_name,
        environment=settings.app_env,
    )

