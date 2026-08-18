from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.schemas.semantic_metrics import (
    Granularity,
    MetricExplanation,
    MetricFilters,
    MetricId,
    SemanticMetric,
)
from app.services.semantic_metrics_service import get_explanation, get_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["semantic metrics"])


@router.get("", response_model=list[SemanticMetric])
def semantic_metrics(
    metric_id: MetricId | None = None,
    organisation: str | None = Query(default=None, min_length=1, max_length=200),
    domain: Literal["electronics", "battery"] | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    granularity: Granularity | None = None,
) -> list[SemanticMetric]:
    try:
        return get_metrics(
            MetricFilters(
                organisation=organisation,
                domain=domain,
                from_date=from_date,
                to_date=to_date,
                granularity=granularity,
            ),
            metric_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Semantic metrics are unavailable.") from exc


@router.get("/{metric_id}/explain", response_model=MetricExplanation)
def explain_metric(metric_id: MetricId) -> MetricExplanation:
    return get_explanation(metric_id)
