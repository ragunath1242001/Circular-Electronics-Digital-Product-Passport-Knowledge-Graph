import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.schemas.observability import ObservabilityMetrics
from app.services.graph_store import GraphStoreError
from app.services.observability_service import get_metrics

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/metrics", response_model=ObservabilityMetrics)
def metrics(
    manufacturer: str | None = Query(default=None, min_length=1, max_length=200),
    supplier: str | None = Query(default=None, min_length=1, max_length=200),
    model: str | None = Query(default=None, min_length=1, max_length=80),
) -> ObservabilityMetrics:
    try:
        return get_metrics(manufacturer, supplier, model)
    except (GraphStoreError, psycopg.Error) as exc:
        raise HTTPException(status_code=503, detail="Semantic metrics are unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
