from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.schemas.semantic_metrics import MetricFilters

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA_SQL = "\n".join(
    (MIGRATIONS / name).read_text(encoding="utf-8")
    for name in (
        "002_ingestion.sql",
        "005_semantic_documents.sql",
        "006_semantic_validation.sql",
        "007_semantic_observations.sql",
        "010_mapping_gap_scope.sql",
    )
)


@dataclass(frozen=True)
class VersionStat:
    version: str
    category: str
    documents: int


@dataclass(frozen=True)
class ConstraintViolation:
    profile: str
    path: str | None
    component: str
    message: str
    violations: int


@dataclass(frozen=True)
class MetricInputs:
    versions: tuple[VersionStat, ...]
    term_categories: dict[str, int]
    term_counts: dict[str, int]
    mapping_terms: dict[str, bool]
    validated: int
    conforming: int
    warnings: int
    profile_validations: dict[str, int]
    class_documents: dict[tuple[str, str], frozenset[str]]
    constraint_violations: tuple[ConstraintViolation, ...]


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


def _filters(filters: MetricFilters) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    values: list[object] = []
    for column, value in (
        ("organisation_id", filters.organisation),
        ("domain", filters.domain),
    ):
        if value is not None:
            clauses.append(f"document.{column} = %s")
            values.append(value)
    if filters.from_date is not None:
        clauses.append("document.ingested_at::date >= %s")
        values.append(filters.from_date)
    if filters.to_date is not None:
        clauses.append("document.ingested_at::date <= %s")
        values.append(filters.to_date)
    return (" AND " + " AND ".join(clauses) if clauses else "", tuple(values))


def load_metric_inputs(filters: MetricFilters) -> MetricInputs:
    where, parameters = _filters(filters)
    with _connect() as connection:
        versions = connection.execute(
            f"""
            SELECT observation.ontology_version AS version, observation.category,
                   COUNT(*) AS documents
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'ontology_version'{where}
            GROUP BY observation.ontology_version, observation.category
            """,
            parameters,
        ).fetchall()
        terms = connection.execute(
            f"""
            SELECT observation.term_iri, observation.category,
                   SUM(observation.occurrence_count) AS occurrences
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'term_classification'{where}
            GROUP BY observation.term_iri, observation.category
            """,
            parameters,
        ).fetchall()
        mappings = connection.execute(
            f"""
            SELECT observation.term_iri,
                   BOOL_OR(observation.observation_type = 'mapping_used') AS mapped
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type IN ('mapping_used', 'mapping_missing'){where}
            GROUP BY observation.term_iri
            """,
            parameters,
        ).fetchall()
        validation = connection.execute(
            f"""
            SELECT COUNT(*) AS validated,
                   COUNT(*) FILTER (WHERE run.violations = 0) AS conforming,
                   COALESCE(SUM(run.warnings), 0) AS warnings
            FROM semantic_validation_runs AS run
            JOIN dpp_documents AS document ON document.document_id = run.document_id
            WHERE TRUE{where}
            """,
            parameters,
        ).fetchone()
        profile_validations = connection.execute(
            f"""
            SELECT run.semantic_profile_id AS profile, COUNT(*) AS validations
            FROM semantic_validation_runs AS run
            JOIN dpp_documents AS document ON document.document_id = run.document_id
            WHERE TRUE{where}
            GROUP BY run.semantic_profile_id
            """,
            parameters,
        ).fetchall()
        class_rows = connection.execute(
            f"""
            SELECT document.semantic_profile_id AS profile,
                   observation.term_iri, observation.document_id
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = 'class_usage'{where}
            """,
            parameters,
        ).fetchall()
        violations = connection.execute(
            f"""
            SELECT run.semantic_profile_id AS profile,
                   observation.result_path AS path,
                   observation.constraint_component AS component,
                   observation.message,
                   COUNT(DISTINCT run.document_id) AS violations
            FROM validation_observations AS observation
            JOIN semantic_validation_runs AS run ON run.id = observation.validation_run_id
            JOIN dpp_documents AS document ON document.document_id = run.document_id
            WHERE observation.constraint_component IS NOT NULL{where}
            GROUP BY run.semantic_profile_id, observation.result_path,
                     observation.constraint_component, observation.message
            """,
            parameters,
        ).fetchall()

    assert validation is not None
    category_counts: defaultdict[str, int] = defaultdict(int)
    term_counts: dict[str, int] = {}
    for row in terms:
        occurrences = int(row["occurrences"])
        category_counts[str(row["category"])] += occurrences
        term_counts[str(row["term_iri"])] = occurrences
    class_documents: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for row in class_rows:
        class_documents[(str(row["profile"]), str(row["term_iri"]))].add(
            str(row["document_id"])
        )
    return MetricInputs(
        versions=tuple(
            VersionStat(
                version=str(row["version"]),
                category=str(row["category"]),
                documents=int(row["documents"]),
            )
            for row in versions
        ),
        term_categories=dict(category_counts),
        term_counts=term_counts,
        mapping_terms={str(row["term_iri"]): bool(row["mapped"]) for row in mappings},
        validated=int(validation["validated"]),
        conforming=int(validation["conforming"]),
        warnings=int(validation["warnings"]),
        profile_validations={
            str(row["profile"]): int(row["validations"]) for row in profile_validations
        },
        class_documents={key: frozenset(value) for key, value in class_documents.items()},
        constraint_violations=tuple(
            ConstraintViolation(
                profile=str(row["profile"]),
                path=str(row["path"]) if row["path"] is not None else None,
                component=str(row["component"]),
                message=str(row["message"]),
                violations=int(row["violations"]),
            )
            for row in violations
        ),
    )


def list_metric_buckets(filters: MetricFilters) -> list[date]:
    if filters.granularity is None:
        return []
    where, parameters = _filters(filters)
    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT date_trunc(%s, document.ingested_at)::date AS bucket_start
            FROM dpp_documents AS document
            WHERE TRUE{where}
            GROUP BY bucket_start ORDER BY bucket_start
            """,
            (filters.granularity, *parameters),
        ).fetchall()
    return [row["bucket_start"] for row in rows if isinstance(row["bucket_start"], date)]
