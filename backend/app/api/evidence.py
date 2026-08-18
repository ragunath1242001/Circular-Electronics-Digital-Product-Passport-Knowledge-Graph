from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, Query

from app.db.evidence import get_evidence, list_evidence, update_evidence
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceCandidateType,
    EvidenceRun,
    EvidenceStatus,
    EvidenceUpdate,
)
from app.services.evidence_service import run_evidence_generation

router = APIRouter(prefix="/api/v1/evidence", tags=["semantic evidence"])


@router.post("/generate", response_model=EvidenceRun)
def generate_evidence() -> EvidenceRun:
    try:
        return run_evidence_generation()
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Evidence generation is unavailable.") from exc


@router.get("", response_model=list[EvidenceCandidate])
def evidence(
    candidate_type: EvidenceCandidateType | None = None,
    status: EvidenceStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[EvidenceCandidate]:
    try:
        return list_evidence(candidate_type, status, limit, offset)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Semantic evidence is unavailable.") from exc


@router.get("/{candidate_id}", response_model=EvidenceCandidate)
def evidence_candidate(candidate_id: UUID) -> EvidenceCandidate:
    try:
        result = get_evidence(candidate_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Semantic evidence is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence candidate not found.")
    return result


@router.patch("/{candidate_id}", response_model=EvidenceCandidate)
def review_evidence(candidate_id: UUID, update: EvidenceUpdate) -> EvidenceCandidate:
    try:
        result = update_evidence(candidate_id, update)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Evidence review is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence candidate not found.")
    return result
