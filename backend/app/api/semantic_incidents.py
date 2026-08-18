from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.db.semantic_incidents import get_incident, list_incidents
from app.schemas.semantic_incidents import (
    DetectorRun,
    DetectorType,
    IncidentSeverity,
    IncidentStatus,
    SemanticIncident,
)
from app.services.drift_detector_service import run_detectors

router = APIRouter(prefix="/api/v1/incidents", tags=["semantic incidents"])


@router.post("/detect", response_model=DetectorRun)
def detect_semantic_drift() -> DetectorRun:
    try:
        return run_detectors()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Drift detection is unavailable.") from exc


@router.get("", response_model=list[SemanticIncident])
def incidents(
    detector_type: DetectorType | None = None,
    severity: IncidentSeverity | None = None,
    status: IncidentStatus | None = "OPEN",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SemanticIncident]:
    try:
        return list_incidents(detector_type, severity, status, limit, offset)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Semantic incidents are unavailable.") from exc


@router.get("/{incident_id}", response_model=SemanticIncident)
def incident(incident_id: UUID) -> SemanticIncident:
    try:
        result = get_incident(incident_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Semantic incidents are unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Semantic incident not found.")
    return result
