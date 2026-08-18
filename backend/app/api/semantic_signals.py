import logging

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.db.semantic_observations import get_signal_summary
from app.schemas.semantic_signals import SignalBatch, SignalSummary
from app.services.graph_store import GraphStoreError
from app.services.semantic_signal_service import collect_pending_documents

router = APIRouter(prefix="/api/v1/signals", tags=["semantic signals"])
logger = logging.getLogger(__name__)


@router.post("/documents", response_model=SignalBatch)
def collect_document_signals(limit: int = Query(default=100, ge=1, le=1_000)) -> SignalBatch:
    try:
        return collect_pending_documents(limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (psycopg.Error, GraphStoreError) as exc:
        logger.exception("semantic_signal_collection_failed")
        raise HTTPException(
            status_code=503, detail="Semantic signal collection is unavailable."
        ) from exc


@router.get("/summary", response_model=SignalSummary)
def signal_summary() -> SignalSummary:
    try:
        return get_signal_summary()
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503, detail="Semantic signal summary is unavailable."
        ) from exc
