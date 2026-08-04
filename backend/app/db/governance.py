import json
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.governance import AuditLog, ReportJob

SCHEMA_SQL = (
    Path(__file__).resolve().parents[2] / "migrations" / "004_governance.sql"
).read_text(encoding="utf-8")
REPORT_COLUMNS = "id, report_type, status, row_count, summary, sources, generated_at"
AUDIT_COLUMNS = "id, actor, action, entity_type, entity_id, result, details, created_at"


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


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _report(row: dict[str, Any]) -> ReportJob:
    values = dict(row)
    values["summary"] = _json(values["summary"])
    values["sources"] = _json(values["sources"])
    return ReportJob.model_validate(values)


def save_report(report: ReportJob, rows: list[dict[str, str]], audit: AuditLog) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO report_jobs
                (id, report_type, status, row_count, summary, sources, content, generated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                report.id,
                report.report_type,
                report.status,
                report.row_count,
                Jsonb(report.summary),
                Jsonb(report.sources),
                Jsonb(rows),
                report.generated_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO audit_logs
                (id, actor, action, entity_type, entity_id, result, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                audit.id,
                audit.actor,
                audit.action,
                audit.entity_type,
                audit.entity_id,
                audit.result,
                Jsonb(audit.details),
                audit.created_at,
            ),
        )


def list_reports(limit: int) -> list[ReportJob]:
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT {REPORT_COLUMNS} FROM report_jobs ORDER BY generated_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [_report(row) for row in rows]


def get_report(report_id: UUID) -> ReportJob | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT {REPORT_COLUMNS} FROM report_jobs WHERE id = %s", (report_id,)
        ).fetchone()
    return _report(row) if row else None


def get_report_rows(report_id: UUID) -> list[dict[str, str]] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT content FROM report_jobs WHERE id = %s", (report_id,)
        ).fetchone()
    return _json(row["content"]) if row else None


def list_audit_logs(limit: int) -> list[AuditLog]:
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT {AUDIT_COLUMNS} FROM audit_logs ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [AuditLog.model_validate({**row, "details": _json(row["details"])}) for row in rows]
