import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.evidence import (
    EvidenceCandidate,
    EvidenceCandidateDraft,
    EvidenceCandidateType,
    EvidenceStatus,
    EvidenceUpdate,
)
from app.schemas.semantic_incidents import SemanticIncident

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA_SQL = "\n".join(
    (MIGRATIONS / name).read_text(encoding="utf-8")
    for name in (
        "002_ingestion.sql",
        "005_semantic_documents.sql",
        "006_semantic_validation.sql",
        "007_semantic_observations.sql",
        "008_semantic_incidents.sql",
        "009_evidence_candidates.sql",
        "010_mapping_gap_scope.sql",
    )
)
EVIDENCE_COLUMNS = """
    id, candidate_key, candidate_type, status, label, affected_concepts,
    first_seen, last_seen, occurrence_count, organisation_count, domain_count,
    trend, growth_rate, persistence_days, mapping_status, conformance_impact,
    metrics, recommendation, source_incident_id, evidence_references,
    evidence_version, annotation, created_at, updated_at
"""


@dataclass(frozen=True)
class ObservationStats:
    first_seen: datetime
    last_seen: datetime
    occurrences: int
    documents: int
    organisations: int
    domains: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class ShaclEvidence:
    profile: str
    path: str | None
    component: str
    message: str
    stats: ObservationStats


def _connect() -> psycopg.Connection[dict[str, Any]]:
    settings = get_settings()
    connection = psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        row_factory=dict_row,
    )
    connection.execute(SCHEMA_SQL)
    return connection


def _stats(row: dict[str, Any], prefix: str) -> ObservationStats:
    return ObservationStats(
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        occurrences=int(row["occurrences"]),
        documents=int(row["documents"]),
        organisations=int(row["organisations"]),
        domains=tuple(str(value) for value in row["domains"]),
        evidence_references=tuple(f"{prefix}:{value}" for value in row["evidence_ids"]),
    )


def load_incident_stats(incidents: list[SemanticIncident]) -> dict[UUID, ObservationStats]:
    results: dict[UUID, ObservationStats] = {}
    with _connect() as connection:
        for incident in incidents:
            clauses: list[str] = []
            parameters: list[object] = []
            if incident.detector_type in {"DET-001", "DET-002", "DET-006"}:
                clauses.append("observation.term_iri = %s")
                parameters.append(incident.dimensions["term_iri"])
            if incident.detector_type == "DET-001":
                clauses.extend(
                    (
                        "observation.observation_type = 'term_classification'",
                        "observation.category = 'unknown'",
                    )
                )
            elif incident.detector_type == "DET-002":
                clauses.extend(
                    (
                        "observation.observation_type = 'term_classification'",
                        "observation.category = 'deprecated'",
                    )
                )
            elif incident.detector_type == "DET-003":
                clauses.extend(
                    (
                        "observation.observation_type = 'ontology_version'",
                        "observation.category = 'deprecated'",
                        "document.domain = %s",
                    )
                )
                parameters.append(incident.dimensions["domain"])
            elif incident.detector_type == "DET-004":
                clauses.extend(
                    (
                        "observation.observation_type = 'term_classification'",
                        "observation.category = 'custom'",
                        "document.domain = %s",
                    )
                )
                parameters.append(incident.dimensions["domain"])
            elif incident.detector_type == "DET-005":
                clauses.extend(
                    (
                        "observation.observation_type = 'term_classification'",
                        "observation.term_iri = ANY(%s)",
                    )
                )
                parameters.append(incident.affected_entities["terms"])
            else:
                clauses.append("observation.observation_type = 'mapping_missing'")
            row = connection.execute(
                f"""
                SELECT MIN(observation.observed_at) AS first_seen,
                       MAX(observation.observed_at) AS last_seen,
                       SUM(observation.occurrence_count) AS occurrences,
                       COUNT(DISTINCT observation.document_id) AS documents,
                       COUNT(DISTINCT document.organisation_id) AS organisations,
                       ARRAY_AGG(DISTINCT document.domain) AS domains,
                       (ARRAY_AGG(observation.id ORDER BY observation.id))[1:100]
                           AS evidence_ids
                FROM semantic_observations AS observation
                JOIN dpp_documents AS document
                  ON document.document_id = observation.document_id
                WHERE {" AND ".join(clauses)}
                """,
                parameters,
            ).fetchone()
            if row is not None and row["first_seen"] is not None:
                results[incident.id] = _stats(row, "semantic_observation")
    return results


def load_shacl_evidence(minimum: int = 100, limit: int = 20) -> list[ShaclEvidence]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT run.semantic_profile_id AS profile, observation.result_path AS path,
                   observation.constraint_component AS component, observation.message,
                   MIN(run.validated_at) AS first_seen,
                   MAX(run.validated_at) AS last_seen,
                   COUNT(*) AS occurrences,
                   COUNT(DISTINCT run.document_id) AS documents,
                   COUNT(DISTINCT run.organisation_id) AS organisations,
                   ARRAY_AGG(DISTINCT run.domain) AS domains,
                   (ARRAY_AGG(observation.id ORDER BY observation.id))[1:100]
                       AS evidence_ids
            FROM validation_observations AS observation
            JOIN semantic_validation_runs AS run ON run.id = observation.validation_run_id
            GROUP BY run.semantic_profile_id, observation.result_path,
                     observation.constraint_component, observation.message
            HAVING COUNT(*) >= %s
            ORDER BY COUNT(*) DESC, run.semantic_profile_id, observation.result_path
            LIMIT %s
            """,
            (minimum, limit),
        ).fetchall()
    return [
        ShaclEvidence(
            profile=str(row["profile"]),
            path=str(row["path"]) if row["path"] is not None else None,
            component=str(row["component"] or "unknown"),
            message=str(row["message"]),
            stats=_stats(row, "validation_observation"),
        )
        for row in rows
    ]


def _candidate(row: dict[str, Any]) -> EvidenceCandidate:
    values = dict(row)
    for field in ("affected_concepts", "metrics", "evidence_references"):
        if isinstance(values[field], str):
            values[field] = json.loads(values[field])
    return EvidenceCandidate.model_validate(values)


def save_evidence(candidates: list[EvidenceCandidateDraft]) -> list[EvidenceCandidate]:
    stored: list[EvidenceCandidate] = []
    active_keys = [candidate.candidate_key for candidate in candidates]
    with _connect() as connection:
        for candidate in candidates:
            row = connection.execute(
                f"""
                INSERT INTO evidence_candidates (
                    id, candidate_key, candidate_type, label, affected_concepts,
                    first_seen, last_seen, occurrence_count, organisation_count,
                    domain_count, trend, growth_rate, persistence_days, mapping_status,
                    conformance_impact, metrics, recommendation, source_incident_id,
                    evidence_references, evidence_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (candidate_key) DO UPDATE SET
                    label = EXCLUDED.label,
                    affected_concepts = EXCLUDED.affected_concepts,
                    first_seen = LEAST(evidence_candidates.first_seen, EXCLUDED.first_seen),
                    last_seen = EXCLUDED.last_seen,
                    occurrence_count = EXCLUDED.occurrence_count,
                    organisation_count = EXCLUDED.organisation_count,
                    domain_count = EXCLUDED.domain_count,
                    trend = EXCLUDED.trend,
                    growth_rate = EXCLUDED.growth_rate,
                    persistence_days = EXCLUDED.persistence_days,
                    mapping_status = EXCLUDED.mapping_status,
                    conformance_impact = EXCLUDED.conformance_impact,
                    metrics = EXCLUDED.metrics,
                    recommendation = EXCLUDED.recommendation,
                    source_incident_id = EXCLUDED.source_incident_id,
                    evidence_references = EXCLUDED.evidence_references,
                    evidence_version = EXCLUDED.evidence_version,
                    updated_at = NOW()
                RETURNING {EVIDENCE_COLUMNS}
                """,
                (
                    candidate.id,
                    candidate.candidate_key,
                    candidate.candidate_type,
                    candidate.label,
                    Jsonb(candidate.affected_concepts),
                    candidate.first_seen,
                    candidate.last_seen,
                    candidate.occurrence_count,
                    candidate.organisation_count,
                    candidate.domain_count,
                    candidate.trend,
                    candidate.growth_rate,
                    candidate.persistence_days,
                    candidate.mapping_status,
                    candidate.conformance_impact,
                    Jsonb(candidate.metrics),
                    candidate.recommendation,
                    candidate.source_incident_id,
                    Jsonb(candidate.evidence_references),
                    candidate.evidence_version,
                ),
            ).fetchone()
            assert row is not None
            stored.append(_candidate(row))
        connection.execute(
            """
            DELETE FROM evidence_candidates
            WHERE status = 'NEW' AND candidate_key::text <> ALL(%s::text[])
            """,
            (active_keys,),
        )
    return stored


def list_evidence(
    candidate_type: EvidenceCandidateType | None,
    status: EvidenceStatus | None,
    limit: int,
    offset: int,
) -> list[EvidenceCandidate]:
    clauses: list[str] = []
    parameters: list[object] = []
    if candidate_type is not None:
        clauses.append("candidate_type = %s")
        parameters.append(candidate_type)
    if status is not None:
        clauses.append("status = %s")
        parameters.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT {EVIDENCE_COLUMNS} FROM evidence_candidates{where} "
            "ORDER BY occurrence_count DESC, id LIMIT %s OFFSET %s",
            (*parameters, limit, offset),
        ).fetchall()
    return [_candidate(row) for row in rows]


def get_evidence(candidate_id: UUID) -> EvidenceCandidate | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT {EVIDENCE_COLUMNS} FROM evidence_candidates WHERE id = %s",
            (candidate_id,),
        ).fetchone()
    return _candidate(row) if row else None


def update_evidence(candidate_id: UUID, update: EvidenceUpdate) -> EvidenceCandidate | None:
    assignments: list[str] = []
    parameters: list[object] = []
    if update.status is not None:
        assignments.append("status = %s")
        parameters.append(update.status)
    if "annotation" in update.model_fields_set:
        assignments.append("annotation = %s")
        parameters.append(update.annotation)
    assignments.append("updated_at = NOW()")
    parameters.append(candidate_id)
    with _connect() as connection:
        row = connection.execute(
            f"""
            UPDATE evidence_candidates SET {", ".join(assignments)}
            WHERE id = %s RETURNING {EVIDENCE_COLUMNS}
            """,
            parameters,
        ).fetchone()
    return _candidate(row) if row else None
