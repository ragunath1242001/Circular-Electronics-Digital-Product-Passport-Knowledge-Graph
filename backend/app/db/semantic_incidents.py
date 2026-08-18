import json
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.semantic_incidents import (
    DetectorType,
    IncidentCandidate,
    IncidentSeverity,
    IncidentStatus,
    SemanticIncident,
)

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA_SQL = "\n".join(
    (MIGRATIONS / name).read_text(encoding="utf-8")
    for name in (
        "002_ingestion.sql",
        "005_semantic_documents.sql",
        "007_semantic_observations.sql",
        "008_semantic_incidents.sql",
        "010_mapping_gap_scope.sql",
    )
)


@dataclass(frozen=True)
class TermSignal:
    term_iri: str
    occurrences: int
    documents: int
    organisations: int
    domains: tuple[str, ...]
    evidence_ids: tuple[int, ...]


@dataclass(frozen=True)
class SharePoint:
    domain: str
    day: date
    numerator: int
    denominator: int


@dataclass(frozen=True)
class DetectorInputs:
    unknown_terms: tuple[TermSignal, ...]
    deprecated_terms: tuple[TermSignal, ...]
    version_shares: tuple[SharePoint, ...]
    custom_shares: tuple[SharePoint, ...]
    mapping_gaps: tuple[TermSignal, ...]
    term_counts: dict[str, int]


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


def _term_signal(row: dict[str, Any]) -> TermSignal:
    return TermSignal(
        term_iri=str(row["term_iri"]),
        occurrences=int(row["occurrences"]),
        documents=int(row["documents"]),
        organisations=int(row["organisations"]),
        domains=tuple(str(value) for value in row["domains"]),
        evidence_ids=tuple(int(value) for value in row["evidence_ids"]),
    )


def load_detector_inputs() -> DetectorInputs:
    with _connect() as connection:
        terms = connection.execute(
            """
            SELECT observation.category, observation.term_iri,
                   SUM(observation.occurrence_count) AS occurrences,
                   COUNT(DISTINCT observation.document_id) AS documents,
                   COUNT(DISTINCT document.organisation_id) AS organisations,
                   ARRAY_AGG(DISTINCT document.domain) AS domains,
                   (ARRAY_AGG(observation.id ORDER BY observation.id))[1:25] AS evidence_ids
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'term_classification'
              AND observation.category IN ('unknown', 'deprecated')
            GROUP BY observation.category, observation.term_iri
            """
        ).fetchall()
        versions = connection.execute(
            """
            SELECT document.domain, document.ingested_at::date AS day,
                   COUNT(*) FILTER (WHERE observation.category = 'deprecated') AS numerator,
                   COUNT(*) FILTER (WHERE observation.category IN ('standard', 'deprecated'))
                       AS denominator
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'ontology_version'
            GROUP BY document.domain, document.ingested_at::date
            ORDER BY document.domain, day
            """
        ).fetchall()
        custom = connection.execute(
            """
            SELECT document.domain, document.ingested_at::date AS day,
                   COALESCE(SUM(observation.occurrence_count)
                       FILTER (WHERE observation.category = 'custom'), 0) AS numerator,
                   SUM(observation.occurrence_count) AS denominator
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'term_classification'
            GROUP BY document.domain, document.ingested_at::date
            ORDER BY document.domain, day
            """
        ).fetchall()
        gaps = connection.execute(
            """
            SELECT observation.term_iri,
                   SUM(observation.occurrence_count) AS occurrences,
                   COUNT(DISTINCT observation.document_id) AS documents,
                   COUNT(DISTINCT document.organisation_id) AS organisations,
                   ARRAY_AGG(DISTINCT document.domain) AS domains,
                   (ARRAY_AGG(observation.id ORDER BY observation.id))[1:25] AS evidence_ids
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'mapping_missing'
            GROUP BY observation.term_iri
            """
        ).fetchall()
        term_counts = connection.execute(
            """
            SELECT term_iri, SUM(occurrence_count) AS occurrences
            FROM semantic_observations
            WHERE observation_type = 'term_classification'
            GROUP BY term_iri
            """
        ).fetchall()
    grouped_terms: dict[str, list[TermSignal]] = {"unknown": [], "deprecated": []}
    for row in terms:
        grouped_terms[str(row["category"])].append(_term_signal(row))
    return DetectorInputs(
        unknown_terms=tuple(grouped_terms["unknown"]),
        deprecated_terms=tuple(grouped_terms["deprecated"]),
        version_shares=tuple(
            SharePoint(
                domain=str(row["domain"]),
                day=row["day"],
                numerator=int(row["numerator"]),
                denominator=int(row["denominator"]),
            )
            for row in versions
        ),
        custom_shares=tuple(
            SharePoint(
                domain=str(row["domain"]),
                day=row["day"],
                numerator=int(row["numerator"]),
                denominator=int(row["denominator"]),
            )
            for row in custom
        ),
        mapping_gaps=tuple(_term_signal(row) for row in gaps),
        term_counts={str(row["term_iri"]): int(row["occurrences"]) for row in term_counts},
    )


def _to_incident(row: dict[str, Any]) -> SemanticIncident:
    values = dict(row)
    for field in (
        "dimensions",
        "affected_entities",
        "observed_values",
        "baseline",
        "evidence_references",
    ):
        if isinstance(values[field], str):
            values[field] = json.loads(values[field])
    return SemanticIncident.model_validate(values)


def save_incidents(
    candidates: list[IncidentCandidate],
    detector_version: str,
) -> list[SemanticIncident]:
    incidents: list[SemanticIncident] = []
    active_keys: list[str] = []
    with _connect() as connection:
        for candidate in candidates:
            incident_key = sha256(
                f"{candidate.detector_version}\x1f{candidate.detector_type}\x1f"
                f"{json.dumps(candidate.dimensions, sort_keys=True)}".encode()
            ).hexdigest()
            active_keys.append(incident_key)
            row = connection.execute(
                """
                INSERT INTO semantic_incidents (
                    id, detector_type, severity, dimensions, affected_entities,
                    observed_values, baseline, threshold_rule, evidence_references,
                    explanation, detector_version, incident_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (incident_key) DO UPDATE SET
                    severity = EXCLUDED.severity,
                    affected_entities = EXCLUDED.affected_entities,
                    observed_values = EXCLUDED.observed_values,
                    baseline = EXCLUDED.baseline,
                    threshold_rule = EXCLUDED.threshold_rule,
                    evidence_references = EXCLUDED.evidence_references,
                    explanation = EXCLUDED.explanation,
                    status = 'OPEN',
                    closed_at = NULL,
                    last_detected_at = NOW()
                RETURNING id, detector_type, severity, status, dimensions,
                          affected_entities, observed_values, baseline, threshold_rule,
                          evidence_references, explanation, detector_version,
                          opened_at, last_detected_at, closed_at
                """,
                (
                    uuid4(),
                    candidate.detector_type,
                    candidate.severity,
                    Jsonb(candidate.dimensions),
                    Jsonb(candidate.affected_entities),
                    Jsonb(candidate.observed_values),
                    Jsonb(candidate.baseline),
                    candidate.threshold_rule,
                    Jsonb(candidate.evidence_references),
                    candidate.explanation,
                    candidate.detector_version,
                    incident_key,
                ),
            ).fetchone()
            assert row is not None
            incidents.append(_to_incident(row))
        connection.execute(
            """
            UPDATE semantic_incidents SET status = 'RESOLVED', closed_at = NOW()
            WHERE detector_version = %s AND status = 'OPEN'
              AND incident_key::text <> ALL(%s::text[])
            """,
            (detector_version, active_keys),
        )
    return incidents


def list_incidents(
    detector_type: DetectorType | None,
    severity: IncidentSeverity | None,
    status: IncidentStatus | None,
    limit: int,
    offset: int,
) -> list[SemanticIncident]:
    clauses: list[str] = []
    parameters: list[object] = []
    for column, value in (
        ("detector_type", detector_type),
        ("severity", severity),
        ("status", status),
    ):
        if value is not None:
            clauses.append(f"{column} = %s")
            parameters.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT id, detector_type, severity, status, dimensions,
                   affected_entities, observed_values, baseline, threshold_rule,
                   evidence_references, explanation, detector_version,
                   opened_at, last_detected_at, closed_at
            FROM semantic_incidents{where}
            ORDER BY last_detected_at DESC, id LIMIT %s OFFSET %s
            """,
            (*parameters, limit, offset),
        ).fetchall()
    return [_to_incident(row) for row in rows]


def get_incident(incident_id: UUID) -> SemanticIncident | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT id, detector_type, severity, status, dimensions,
                   affected_entities, observed_values, baseline, threshold_rule,
                   evidence_references, explanation, detector_version,
                   opened_at, last_detected_at, closed_at
            FROM semantic_incidents WHERE id = %s
            """,
            (incident_id,),
        ).fetchone()
    return _to_incident(row) if row else None
