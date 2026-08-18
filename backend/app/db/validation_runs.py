import json
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.validation import (
    DocumentValidation,
    StoredSemanticDocument,
    ValidationReport,
    ValidationSummary,
)

SCHEMA_SQL = (
    Path(__file__).resolve().parents[2] / "migrations" / "001_validation_runs.sql"
).read_text(encoding="utf-8")
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"
SEMANTIC_SCHEMA_SQL = "\n".join(
    (MIGRATIONS / name).read_text(encoding="utf-8")
    for name in ("002_ingestion.sql", "005_semantic_documents.sql", "006_semantic_validation.sql")
)


def _connect() -> psycopg.Connection[dict[str, Any]]:
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        row_factory=dict_row,
    )


def save_validation_run(report: ValidationReport, report_turtle: str) -> None:
    with _connect() as connection:
        connection.execute(SCHEMA_SQL)
        connection.execute(
            """
            INSERT INTO validation_runs
                (id, conforms, created_at, violations, warnings, info, results, report_turtle)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                report.id,
                report.conforms,
                report.created_at,
                report.violations,
                report.warnings,
                report.info,
                Jsonb([result.model_dump() for result in report.results]),
                report_turtle,
            ),
        )


def _to_report(row: dict[str, Any]) -> ValidationReport:
    values = dict(row)
    if isinstance(values["results"], str):
        values["results"] = json.loads(values["results"])
    values.pop("report_turtle", None)
    return ValidationReport.model_validate(values)


def list_validation_runs(limit: int = 50) -> list[ValidationReport]:
    with _connect() as connection:
        connection.execute(SCHEMA_SQL)
        rows = connection.execute(
            """
            SELECT id, conforms, created_at, violations, warnings, info, results
            FROM validation_runs ORDER BY created_at DESC LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [_to_report(row) for row in rows]


def get_validation_run(run_id: UUID) -> ValidationReport | None:
    with _connect() as connection:
        connection.execute(SCHEMA_SQL)
        row = connection.execute(
            """
            SELECT id, conforms, created_at, violations, warnings, info, results
            FROM validation_runs WHERE id = %s
            """,
            (run_id,),
        ).fetchone()
    return _to_report(row) if row else None


def list_pending_documents(limit: int) -> list[StoredSemanticDocument]:
    with _connect() as connection:
        connection.execute(SEMANTIC_SCHEMA_SQL)
        rows = connection.execute(
            """
            SELECT document_id, organisation_id, domain, semantic_profile_id,
                   declared_ontology_version, graph_uri
            FROM dpp_documents AS document
            WHERE NOT EXISTS (
                SELECT 1 FROM semantic_validation_runs AS run
                WHERE run.document_id = document.document_id
            )
            ORDER BY document.ingested_at, document.document_id
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [StoredSemanticDocument.model_validate(row) for row in rows]


def save_document_validations(validations: list[DocumentValidation]) -> None:
    if not validations:
        return
    with _connect() as connection:
        connection.execute(SEMANTIC_SCHEMA_SQL)
        for validation in validations:
            document, report = validation.document, validation.report
            inserted = connection.execute(
                """
                INSERT INTO semantic_validation_runs (
                    id, document_id, organisation_id, domain, semantic_profile_id,
                    declared_ontology_version, conforms, violations, warnings, info, validated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO NOTHING
                RETURNING id
                """,
                (
                    report.id,
                    document.document_id,
                    document.organisation_id,
                    document.domain,
                    document.semantic_profile_id,
                    document.declared_ontology_version,
                    report.conforms,
                    report.violations,
                    report.warnings,
                    report.info,
                    report.created_at,
                ),
            ).fetchone()
            if inserted is None:
                continue
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO validation_observations (
                        validation_run_id, focus_node_hash, result_path, constraint_component,
                        source_shape, severity, message_code, message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            report.id,
                            sha256(result.focus_node.encode()).hexdigest(),
                            result.path,
                            result.constraint_component,
                            result.source_shape,
                            result.severity,
                            sha256(
                                "\x1f".join(
                                    (
                                        result.constraint_component or "",
                                        result.path or "",
                                        result.severity,
                                        result.message,
                                    )
                                ).encode()
                            ).hexdigest()[:16],
                            result.message,
                        )
                        for result in report.results
                    ],
                )


def get_validation_summary() -> ValidationSummary:
    with _connect() as connection:
        connection.execute(SEMANTIC_SCHEMA_SQL)
        row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM dpp_documents) AS total_documents,
                COUNT(*) AS validated_documents,
                COUNT(*) FILTER (WHERE conforms) AS conforming_documents,
                COUNT(*) FILTER (WHERE NOT conforms) AS nonconforming_documents,
                COALESCE(SUM(violations), 0) AS violations,
                COALESCE(SUM(warnings), 0) AS warnings,
                COALESCE(SUM(info), 0) AS info
            FROM semantic_validation_runs
            """
        ).fetchone()
    assert row is not None
    validated = int(row["validated_documents"])
    conforming = int(row["conforming_documents"])
    return ValidationSummary(
        **row,
        conformance_rate=round(conforming / validated, 4) if validated else 0.0,
    )
