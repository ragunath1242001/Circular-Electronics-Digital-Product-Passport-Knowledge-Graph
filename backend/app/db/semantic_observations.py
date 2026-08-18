from hashlib import sha256
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.schemas.semantic_signals import SemanticObservation, SignalSummary
from app.schemas.validation import StoredSemanticDocument

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SCHEMA_SQL = "\n".join(
    (MIGRATIONS / name).read_text(encoding="utf-8")
    for name in (
        "002_ingestion.sql",
        "005_semantic_documents.sql",
        "007_semantic_observations.sql",
        "010_mapping_gap_scope.sql",
    )
)


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


def list_pending_documents(limit: int) -> list[StoredSemanticDocument]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT document_id, organisation_id, domain, semantic_profile_id,
                   declared_ontology_version, graph_uri
            FROM dpp_documents AS document
            WHERE NOT EXISTS (
                SELECT 1 FROM semantic_observations AS observation
                WHERE observation.document_id = document.document_id
            )
            ORDER BY document.ingested_at, document.document_id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [StoredSemanticDocument.model_validate(row) for row in rows]


def save_observations(observations: list[SemanticObservation]) -> None:
    if not observations:
        return
    with _connect() as connection, connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO semantic_observations (
                document_id, observation_type, term_iri, namespace, category,
                ontology_version, occurrence_count, observed_at, observation_hash
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (observation_hash) DO NOTHING
            """,
            [
                (
                    item.document_id,
                    item.observation_type,
                    item.term_iri,
                    item.namespace,
                    item.category,
                    item.ontology_version,
                    item.occurrence_count,
                    item.observed_at,
                    sha256(
                        "\x1f".join(
                            (
                                item.document_id,
                                item.observation_type,
                                item.term_iri or "",
                                item.namespace or "",
                                item.category or "",
                                item.ontology_version or "",
                            )
                        ).encode()
                    ).hexdigest(),
                )
                for item in observations
            ],
        )


def get_signal_summary() -> SignalSummary:
    with _connect() as connection:
        totals = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM dpp_documents) AS total_documents,
                COUNT(DISTINCT document_id) AS collected_documents,
                COUNT(*) AS observations,
                COALESCE(SUM(occurrence_count), 0) AS occurrences
            FROM semantic_observations
            """
        ).fetchone()
        by_type = connection.execute(
            """
            SELECT observation_type, COUNT(*) AS count
            FROM semantic_observations GROUP BY observation_type ORDER BY observation_type
            """
        ).fetchall()
        by_category = connection.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM semantic_observations
            WHERE category IS NOT NULL GROUP BY category ORDER BY category
            """
        ).fetchall()
    assert totals is not None
    return SignalSummary(
        **totals,
        by_type={str(row["observation_type"]): int(row["count"]) for row in by_type},
        by_category={str(row["category"]): int(row["count"]) for row in by_category},
    )
