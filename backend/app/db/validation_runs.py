import json
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.validation import ValidationReport

SCHEMA_SQL = (
    Path(__file__).resolve().parents[2] / "migrations" / "001_validation_runs.sql"
).read_text(encoding="utf-8")


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
