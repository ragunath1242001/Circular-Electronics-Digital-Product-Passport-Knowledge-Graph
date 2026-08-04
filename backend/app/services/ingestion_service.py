import csv
import hashlib
import io
import json
from typing import Any

from pydantic import ValidationError

from app.db.ingestion import (
    create_ingestion_job,
    record_exists,
    save_ingested_record,
    save_ingestion_error,
    update_ingestion_job,
)
from app.db.validation_runs import save_validation_run
from app.schemas.ingestion import IngestionJob, JobStatus, SmartphoneRecord
from app.semantic.graph_builder import MAPPING_VERSION, record_to_graph
from app.semantic.uri_factory import slugify
from app.services.graph_store import put_graph
from app.services.validation_service import validate_data


class IngestionFormatError(ValueError):
    """Raised when an upload cannot be decoded as its declared format."""


def parse_records(content: str, data_format: str) -> list[dict[str, Any]]:
    try:
        if data_format == "csv":
            records = list(csv.DictReader(io.StringIO(content)))
        elif data_format == "json":
            decoded = json.loads(content)
            records = decoded if isinstance(decoded, list) else [decoded]
        else:
            raise IngestionFormatError(f"Unsupported format: {data_format}")
    except (csv.Error, json.JSONDecodeError) as exc:
        raise IngestionFormatError(f"Invalid {data_format} file: {exc}") from exc
    if not records or not all(isinstance(record, dict) for record in records):
        raise IngestionFormatError("The upload must contain at least one object record.")
    return records


def record_hash(record: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"mapping_version": MAPPING_VERSION, "record": record},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _validation_message(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )


def run_ingestion(
    content: str,
    data_format: str,
    source_system: str,
    file_name: str,
) -> IngestionJob:
    job = create_ingestion_job(source_system, file_name, data_format, MAPPING_VERSION)
    total = imported = duplicates = quarantined = 0
    try:
        records = parse_records(content, data_format)
        total = len(records)
        update_ingestion_job(job.id, "RUNNING", total_records=total)
        update_ingestion_job(job.id, "MAPPING", total_records=total)
        validation_started = False
        has_warnings = False

        for record_number, raw_record in enumerate(records, start=1):
            digest = record_hash(raw_record)
            if record_exists(source_system, digest):
                duplicates += 1
                continue
            try:
                record = SmartphoneRecord.model_validate(raw_record)
                graph = record_to_graph(record, source_system, job.id)
            except ValidationError as exc:
                quarantined += 1
                save_ingestion_error(
                    job.id,
                    record_number,
                    str(raw_record.get("product_identifier") or "") or None,
                    "MAPPING_VALIDATION_FAILED",
                    _validation_message(exc),
                    raw_record,
                )
                continue
            except ValueError as exc:
                quarantined += 1
                save_ingestion_error(
                    job.id,
                    record_number,
                    str(raw_record.get("product_identifier") or "") or None,
                    "URI_GENERATION_FAILED",
                    str(exc),
                    raw_record,
                )
                continue

            if not validation_started:
                update_ingestion_job(
                    job.id,
                    "VALIDATING",
                    total,
                    imported,
                    duplicates,
                    quarantined,
                )
                validation_started = True
            outcome = validate_data(str(graph.serialize(format="turtle")))
            save_validation_run(outcome.report, outcome.report_turtle)
            has_warnings = has_warnings or bool(outcome.report.warnings or outcome.report.info)
            if not outcome.report.conforms:
                quarantined += 1
                save_ingestion_error(
                    job.id,
                    record_number,
                    record.product_identifier,
                    "SHACL_VALIDATION_FAILED",
                    "; ".join(result.message for result in outcome.report.results),
                    raw_record,
                )
                continue

            graph_uri = f"urn:dpp:graph:passport:{slugify(record.product_identifier)}"
            graph_data = graph.serialize(format="turtle", encoding="utf-8")
            assert isinstance(graph_data, bytes)
            put_graph(graph_data, graph_uri)
            save_ingested_record(
                source_system,
                record.product_identifier,
                digest,
                MAPPING_VERSION,
                graph_uri,
            )
            imported += 1

        if quarantined == total:
            final_status: JobStatus = "QUARANTINED"
        elif quarantined or has_warnings:
            final_status = "COMPLETED_WITH_WARNINGS"
        else:
            final_status = "COMPLETED"
        return update_ingestion_job(
            job.id,
            final_status,
            total,
            imported,
            duplicates,
            quarantined,
        )
    except Exception as exc:
        update_ingestion_job(
            job.id,
            "FAILED",
            total,
            imported,
            duplicates,
            quarantined,
            str(exc),
        )
        raise
