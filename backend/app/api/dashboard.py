from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, HTTPException, Path, Query

from app.db.dashboard import (
    get_constraint_usage,
    list_constraint_usage,
    list_term_usage,
    load_adoption,
    load_ecosystem_counts,
    load_organisation,
)
from app.schemas.dashboard import (
    ConstraintUsage,
    EcosystemSummary,
    OntologyAdoption,
    OrganisationOverview,
    TermUsage,
)
from app.schemas.semantic_metrics import MetricFilters
from app.services.semantic_metrics_service import get_metrics
from app.services.semantic_registry import get_registry

router = APIRouter(prefix="/api/v1", tags=["observatory dashboard"])


@router.get("/ecosystem/summary", response_model=EcosystemSummary)
def ecosystem_summary(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> EcosystemSummary:
    try:
        counts = load_ecosystem_counts()
        metrics = get_metrics(MetricFilters(from_date=from_date, to_date=to_date))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Ecosystem summary is unavailable.") from exc
    return EcosystemSummary(
        **counts,
        main_metrics={item.metric_id: item.value for item in metrics},
    )


def _terms(
    category: Literal["unknown", "deprecated", "custom"],
    limit: int,
    offset: int,
) -> list[TermUsage]:
    try:
        return list_term_usage(category, limit, offset)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Term telemetry is unavailable.") from exc


@router.get("/terms/unknown", response_model=list[TermUsage])
def unknown_terms(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TermUsage]:
    return _terms("unknown", limit, offset)


@router.get("/terms/deprecated", response_model=list[TermUsage])
def deprecated_terms(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TermUsage]:
    return _terms("deprecated", limit, offset)


@router.get("/terms/custom", response_model=list[TermUsage])
def custom_terms(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TermUsage]:
    return _terms("custom", limit, offset)


@router.get("/validation/constraints", response_model=list[ConstraintUsage])
def constraints(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ConstraintUsage]:
    try:
        return list_constraint_usage(limit, offset)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Constraint telemetry is unavailable.") from exc


@router.get("/validation/constraints/{constraint_id}", response_model=ConstraintUsage)
def constraint(constraint_id: str = Path(pattern=r"^[0-9a-f]{16}$")) -> ConstraintUsage:
    try:
        result = get_constraint_usage(constraint_id)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Constraint telemetry is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Constraint not found.")
    return result


@router.get("/ontologies/{ontology_id}/adoption", response_model=OntologyAdoption)
def ontology_adoption(ontology_id: str = Path(min_length=1, max_length=80)) -> OntologyAdoption:
    ontology = next((item for item in get_registry().ontologies if item.id == ontology_id), None)
    if ontology is None:
        raise HTTPException(status_code=404, detail="Ontology not found.")
    profile_versions = None
    if ontology_id != "products":
        profile_versions = {
            profile.id: version
            for profile in get_registry().profiles
            if (version := profile.ontology_versions.get(ontology_id)) is not None
        }
    try:
        values = load_adoption(ontology.current_version, profile_versions)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Ontology adoption is unavailable.") from exc
    return OntologyAdoption(
        ontology_id=ontology_id,
        current_version=ontology.current_version,
        **values,
    )


@router.get("/mappings/gaps", response_model=list[TermUsage])
def mapping_gaps(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[TermUsage]:
    try:
        return list_term_usage("mapping_missing", limit, offset)
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail="Mapping gaps are unavailable.") from exc


@router.get("/ecosystem/organisations/{organisation_id}", response_model=OrganisationOverview)
def organisation(
    organisation_id: str = Path(min_length=1, max_length=200),
) -> OrganisationOverview:
    try:
        values = load_organisation(organisation_id)
        metrics = get_metrics(MetricFilters(organisation=organisation_id))
    except psycopg.Error as exc:
        raise HTTPException(
            status_code=503, detail="Organisation telemetry is unavailable."
        ) from exc
    if values is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    return OrganisationOverview(
        **values,
        metric_values={item.metric_id: item.value for item in metrics},
    )
