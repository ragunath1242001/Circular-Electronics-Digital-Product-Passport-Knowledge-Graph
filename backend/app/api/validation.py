import logging
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Query, status

from app.db.validation_runs import get_validation_run, list_validation_runs, save_validation_run
from app.schemas.validation import ValidationReport, ValidationRequest
from app.services.validation_service import InvalidRdfError, validate_data

router = APIRouter(prefix="/api/v1/validation", tags=["validation"])
logger = logging.getLogger(__name__)


@router.post("/runs", response_model=ValidationReport, status_code=status.HTTP_201_CREATED)
def create_validation_run(request: ValidationRequest) -> ValidationReport:
    try:
        outcome = validate_data(request.data, request.format)
        save_validation_run(outcome.report, outcome.report_turtle)
    except InvalidRdfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.exception("validation_report_persistence_failed")
        raise HTTPException(
            status_code=503,
            detail="Validation report could not be persisted.",
        ) from exc
    logger.info(
        "validation_completed",
        extra={"validation_run_id": str(outcome.report.id), "conforms": outcome.report.conforms},
    )
    return outcome.report


@router.get("/runs", response_model=list[ValidationReport])
def get_validation_runs(limit: int = Query(default=50, ge=1, le=200)) -> list[ValidationReport]:
    try:
        return list_validation_runs(limit)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Validation reports are unavailable.") from exc


@router.get("/runs/{run_id}", response_model=ValidationReport)
def get_validation_run_by_id(run_id: UUID) -> ValidationReport:
    try:
        report = get_validation_run(run_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Validation reports are unavailable.") from exc
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found.")
    return report
