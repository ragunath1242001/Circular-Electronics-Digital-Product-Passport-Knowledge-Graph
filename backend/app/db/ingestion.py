from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import get_settings
from app.schemas.ingestion import IngestionError, IngestionJob, JobStatus

SCHEMA_SQL = (
    Path(__file__).resolve().parents[2] / "migrations" / "002_ingestion.sql"
).read_text(encoding="utf-8")
JOB_COLUMNS = """
id, source_system, file_name, data_format, mapping_version, status,
total_records, imported_records, duplicate_records, quarantined_records,
created_at, completed_at, error_message
"""


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


def create_ingestion_job(
    source_system: str,
    file_name: str,
    data_format: str,
    mapping_version: str,
) -> IngestionJob:
    with _connect() as connection:
        row = connection.execute(
            f"""
            INSERT INTO ingestion_jobs
                (id, source_system, file_name, data_format, mapping_version, status)
            VALUES (%s, %s, %s, %s, %s, 'PENDING')
            RETURNING {JOB_COLUMNS}
            """,
            (uuid4(), source_system, file_name, data_format, mapping_version),
        ).fetchone()
    assert row is not None
    return IngestionJob.model_validate(row)


def update_ingestion_job(
    job_id: UUID,
    status: JobStatus,
    total_records: int = 0,
    imported_records: int = 0,
    duplicate_records: int = 0,
    quarantined_records: int = 0,
    error_message: str | None = None,
) -> IngestionJob:
    completed = status in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED", "QUARANTINED"}
    with _connect() as connection:
        row = connection.execute(
            f"""
            UPDATE ingestion_jobs SET
                status = %s,
                total_records = %s,
                imported_records = %s,
                duplicate_records = %s,
                quarantined_records = %s,
                completed_at = CASE WHEN %s THEN NOW() ELSE completed_at END,
                error_message = %s
            WHERE id = %s
            RETURNING {JOB_COLUMNS}
            """,
            (
                status,
                total_records,
                imported_records,
                duplicate_records,
                quarantined_records,
                completed,
                error_message,
                job_id,
            ),
        ).fetchone()
    assert row is not None
    return IngestionJob.model_validate(row)


def record_exists(source_system: str, record_hash: str) -> bool:
    with _connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM ingested_records WHERE source_system = %s AND record_hash = %s",
            (source_system, record_hash),
        ).fetchone()
    return row is not None


def save_ingested_record(
    source_system: str,
    product_identifier: str,
    record_hash: str,
    mapping_version: str,
    graph_uri: str,
) -> None:
    # ponytail: per-record transaction; batch writes when 1,000-record imports are benchmarked.
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO ingested_records
                (source_system, product_identifier, record_hash, mapping_version, graph_uri)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_system, record_hash) DO NOTHING
            """,
            (source_system, product_identifier, record_hash, mapping_version, graph_uri),
        )


def save_ingestion_error(
    job_id: UUID,
    record_number: int,
    product_identifier: str | None,
    error_code: str,
    message: str,
    raw_record: dict[str, Any],
) -> None:
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO ingestion_errors
                (job_id, record_number, product_identifier, error_code, message, raw_record)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (job_id, record_number, product_identifier, error_code, message, Jsonb(raw_record)),
        )


def get_ingestion_job(job_id: UUID) -> IngestionJob | None:
    with _connect() as connection:
        row = connection.execute(
            f"SELECT {JOB_COLUMNS} FROM ingestion_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    return IngestionJob.model_validate(row) if row else None


def list_ingestion_jobs(limit: int = 50) -> list[IngestionJob]:
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT {JOB_COLUMNS} FROM ingestion_jobs ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()
    return [IngestionJob.model_validate(row) for row in rows]


def list_ingestion_errors(job_id: UUID) -> list[IngestionError]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, job_id, record_number, product_identifier, error_code,
                   message, raw_record, created_at
            FROM ingestion_errors WHERE job_id = %s ORDER BY record_number
            """,
            (job_id,),
        ).fetchall()
    return [IngestionError.model_validate(row) for row in rows]

