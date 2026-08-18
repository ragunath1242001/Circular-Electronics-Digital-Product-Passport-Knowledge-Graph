from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.schemas.dashboard import ConstraintUsage, OrganisationAdoption, TermUsage

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
TermCategory = Literal["unknown", "deprecated", "custom", "mapping_missing"]


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


def load_ecosystem_counts() -> dict[str, Any]:
    with _connect() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS documents, COUNT(DISTINCT organisation_id) AS organisations "
            "FROM dpp_documents"
        ).fetchone()
        domains = connection.execute(
            "SELECT domain, COUNT(*) AS documents FROM dpp_documents GROUP BY domain"
        ).fetchall()
        versions = connection.execute(
            "SELECT declared_ontology_version AS version, COUNT(*) AS documents "
            "FROM dpp_documents GROUP BY declared_ontology_version"
        ).fetchall()
    assert total is not None
    return {
        "documents": int(total["documents"]),
        "organisations": int(total["organisations"]),
        "domains": {str(row["domain"]): int(row["documents"]) for row in domains},
        "ontology_versions": {
            str(row["version"]): int(row["documents"]) for row in versions
        },
        "generated_at": datetime.now(UTC),
    }


def list_term_usage(
    category: TermCategory,
    limit: int,
    offset: int,
) -> list[TermUsage]:
    observation_type = "mapping_missing" if category == "mapping_missing" else "term_classification"
    category_clause = "" if category == "mapping_missing" else "AND observation.category = %s"
    parameters: tuple[object, ...] = (
        (observation_type, limit, offset)
        if category == "mapping_missing"
        else (observation_type, category, limit, offset)
    )
    with _connect() as connection:
        rows = connection.execute(
            f"""
            SELECT observation.term_iri,
                   SUM(observation.occurrence_count) AS occurrences,
                   COUNT(DISTINCT observation.document_id) AS documents,
                   COUNT(DISTINCT document.organisation_id) AS organisations,
                   ARRAY_AGG(DISTINCT document.domain) AS domains,
                   MIN(observation.observed_at) AS first_seen,
                   MAX(observation.observed_at) AS last_seen
            FROM semantic_observations AS observation
            JOIN dpp_documents AS document ON document.document_id = observation.document_id
            WHERE observation.observation_type = %s {category_clause}
            GROUP BY observation.term_iri
            ORDER BY occurrences DESC, observation.term_iri
            LIMIT %s OFFSET %s
            """,
            parameters,
        ).fetchall()
    return [
        TermUsage(
            term_iri=str(row["term_iri"]),
            category=category,
            occurrences=int(row["occurrences"]),
            documents=int(row["documents"]),
            organisations=int(row["organisations"]),
            domains=[str(value) for value in row["domains"]],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
        )
        for row in rows
    ]


def _constraint(row: dict[str, Any]) -> ConstraintUsage:
    identity = "\x1f".join(
        str(row[field] or "") for field in ("profile", "path", "component", "message")
    )
    return ConstraintUsage(
        id=sha256(identity.encode()).hexdigest()[:16],
        profile=str(row["profile"]),
        path=str(row["path"]) if row["path"] is not None else None,
        component=str(row["component"] or "unknown"),
        severity=str(row["severity"]),
        message=str(row["message"]),
        violations=int(row["violations"]),
        documents=int(row["documents"]),
        organisations=int(row["organisations"]),
        domains=[str(value) for value in row["domains"]],
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        evidence_references=[
            f"validation_observation:{value}" for value in row["evidence_ids"]
        ],
    )


def list_constraint_usage(limit: int, offset: int = 0) -> list[ConstraintUsage]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT run.semantic_profile_id AS profile, observation.result_path AS path,
                   observation.constraint_component AS component, observation.severity,
                   observation.message, COUNT(*) AS violations,
                   COUNT(DISTINCT run.document_id) AS documents,
                   COUNT(DISTINCT run.organisation_id) AS organisations,
                   ARRAY_AGG(DISTINCT run.domain) AS domains,
                   MIN(run.validated_at) AS first_seen, MAX(run.validated_at) AS last_seen,
                   (ARRAY_AGG(observation.id ORDER BY observation.id))[1:100]
                       AS evidence_ids
            FROM validation_observations AS observation
            JOIN semantic_validation_runs AS run ON run.id = observation.validation_run_id
            GROUP BY run.semantic_profile_id, observation.result_path,
                     observation.constraint_component, observation.severity, observation.message
            ORDER BY violations DESC, run.semantic_profile_id, observation.result_path
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return [_constraint(row) for row in rows]


def get_constraint_usage(constraint_id: str) -> ConstraintUsage | None:
    # ponytail: constraints are a small registry-backed set; add a persisted key if it exceeds 500.
    return next(
        (item for item in list_constraint_usage(500) if item.id == constraint_id),
        None,
    )


def load_adoption(
    current_version: str,
    profile_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    if profile_versions is not None:
        with _connect() as connection:
            rows = connection.execute(
                """
                SELECT semantic_profile_id AS profile, organisation_id,
                       COUNT(*) AS documents
                FROM dpp_documents
                GROUP BY semantic_profile_id, organisation_id
                """
            ).fetchall()
        distribution: dict[str, int] = {}
        profile_organisations: dict[str, list[int]] = {}
        for row in rows:
            version = profile_versions.get(str(row["profile"]), "unresolved")
            count = int(row["documents"])
            distribution[version] = distribution.get(version, 0) + count
            totals = profile_organisations.setdefault(str(row["organisation_id"]), [0, 0])
            totals[0] += count
            totals[1] += count if version == current_version else 0
        total = sum(distribution.values())
        current = distribution.get(current_version, 0)
        return {
            "documents": total,
            "current_documents": current,
            "adoption_rate": round(current / total, 4) if total else 0.0,
            "version_distribution": distribution,
            "lagging_organisations": [
                OrganisationAdoption(
                    organisation_id=organisation_id,
                    documents=values[0],
                    current_documents=values[1],
                    adoption_rate=round(values[1] / values[0], 4),
                )
                for organisation_id, values in sorted(
                    profile_organisations.items(),
                    key=lambda item: (item[1][1] / item[1][0], item[0]),
                )
                if values[1] < values[0]
            ],
        }
    with _connect() as connection:
        versions = connection.execute(
            "SELECT declared_ontology_version AS version, COUNT(*) AS documents "
            "FROM dpp_documents GROUP BY declared_ontology_version"
        ).fetchall()
        organisations = connection.execute(
            """
            SELECT organisation_id, COUNT(*) AS documents,
                   COUNT(*) FILTER (WHERE declared_ontology_version = %s) AS current_documents
            FROM dpp_documents GROUP BY organisation_id
            ORDER BY COUNT(*) FILTER (WHERE declared_ontology_version = %s)::float
                     / COUNT(*), organisation_id
            """,
            (current_version, current_version),
        ).fetchall()
    distribution = {str(row["version"]): int(row["documents"]) for row in versions}
    total = sum(distribution.values())
    current = distribution.get(current_version, 0)
    return {
        "documents": total,
        "current_documents": current,
        "adoption_rate": round(current / total, 4) if total else 0.0,
        "version_distribution": distribution,
        "lagging_organisations": [
            OrganisationAdoption(
                organisation_id=str(row["organisation_id"]),
                documents=int(row["documents"]),
                current_documents=int(row["current_documents"]),
                adoption_rate=round(int(row["current_documents"]) / int(row["documents"]), 4),
            )
            for row in organisations
            if int(row["current_documents"]) < int(row["documents"])
        ],
    }


def load_organisation(organisation_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT domain, semantic_profile_id AS profile,
                   declared_ontology_version AS version, COUNT(*) AS documents
            FROM dpp_documents WHERE organisation_id = %s
            GROUP BY domain, semantic_profile_id, declared_ontology_version
            """,
            (organisation_id,),
        ).fetchall()
        validation = connection.execute(
            """
            SELECT COUNT(*) AS validated,
                   COUNT(*) FILTER (WHERE violations = 0) AS conforming
            FROM semantic_validation_runs WHERE organisation_id = %s
            """,
            (organisation_id,),
        ).fetchone()
    if not rows:
        return None
    domains: dict[str, int] = {}
    profiles: dict[str, int] = {}
    versions: dict[str, int] = {}
    for row in rows:
        count = int(row["documents"])
        domains[str(row["domain"])] = domains.get(str(row["domain"]), 0) + count
        profiles[str(row["profile"])] = profiles.get(str(row["profile"]), 0) + count
        versions[str(row["version"])] = versions.get(str(row["version"]), 0) + count
    assert validation is not None
    validated = int(validation["validated"])
    return {
        "organisation_id": organisation_id,
        "documents": sum(domains.values()),
        "domains": domains,
        "profiles": profiles,
        "ontology_versions": versions,
        "conformance_rate": (
            round(int(validation["conforming"]) / validated, 4) if validated else 0.0
        ),
    }
