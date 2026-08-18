import csv
import hashlib
import io
import json
from typing import Any, BinaryIO, cast
from uuid import UUID

from pydantic import ValidationError
from rdflib import Dataset, Graph, URIRef

from app.db.ingestion import (
    create_ingestion_job,
    load_semantic_document_keys,
    record_exists,
    save_ingested_record,
    save_ingestion_error,
    save_semantic_documents,
    update_ingestion_job,
)
from app.db.validation_runs import save_validation_run
from app.schemas.ingestion import (
    IngestionJob,
    JobStatus,
    SemanticDocumentEnvelope,
    SmartphoneRecord,
)
from app.semantic.graph_builder import MAPPING_VERSION, record_to_graph
from app.semantic.uri_factory import slugify
from app.services.graph_store import post_dataset, put_graph
from app.services.validation_service import validate_data


class IngestionFormatError(ValueError):
    """Raised when an upload cannot be decoded as its declared format."""


SEMANTIC_INGESTION_VERSION = "semantic-jsonld-1.0"
MAX_JSONL_LINE_BYTES = 1_000_000
BATCH_SIZE = 100


class SemanticDocumentError(ValueError):
    def __init__(self, code: str, message: str, raw_record: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.raw_record = raw_record


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


def semantic_document_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _reject_remote_contexts(payload: dict[str, Any]) -> None:
    pending: list[object] = [payload]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            context = value.get("@context")
            if isinstance(context, str) or (
                isinstance(context, list) and any(isinstance(item, str) for item in context)
            ):
                raise ValueError("Remote JSON-LD contexts are not allowed.")
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def _error_record(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        record = cast(dict[str, Any], value)
        return {
            key: record[key]
            for key in ("document_id", "external_identifier", "organisation_id", "domain")
            if key in record
        }
    return {"raw": str(value)[:1000]}


def _parse_semantic_line(raw_line: bytes) -> tuple[SemanticDocumentEnvelope, Graph]:
    if len(raw_line) > MAX_JSONL_LINE_BYTES:
        raise SemanticDocumentError(
            "JSONL_LINE_TOO_LARGE",
            "A JSONL record exceeds the 1 MB limit.",
            {},
        )
    try:
        text = raw_line.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SemanticDocumentError("JSONL_DECODE_FAILED", "Record is not UTF-8.", {}) from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SemanticDocumentError(
            "JSONL_PARSE_FAILED",
            f"Invalid JSON: {exc.msg}.",
            _error_record(text),
        ) from exc
    try:
        envelope = SemanticDocumentEnvelope.model_validate(raw)
    except ValidationError as exc:
        raise SemanticDocumentError(
            "ENVELOPE_VALIDATION_FAILED",
            _validation_message(exc),
            _error_record(raw),
        ) from exc
    if semantic_document_hash(envelope.payload) != envelope.document_hash:
        raise SemanticDocumentError(
            "DOCUMENT_HASH_MISMATCH",
            "Document hash does not match the canonical JSON-LD payload.",
            _error_record(raw),
        )
    try:
        _reject_remote_contexts(envelope.payload)
        graph = Graph().parse(
            data=json.dumps(envelope.payload, ensure_ascii=False),
            format="json-ld",
        )
    except Exception as exc:
        raise SemanticDocumentError(
            "JSONLD_PARSE_FAILED",
            f"Invalid JSON-LD: {exc}",
            _error_record(raw),
        ) from exc
    if not graph:
        raise SemanticDocumentError(
            "JSONLD_PARSE_FAILED",
            "JSON-LD payload produced an empty graph.",
            _error_record(raw),
        )
    return envelope, graph


def _flush_semantic_batch(
    job_id: UUID,
    source_system: str,
    batch: list[tuple[SemanticDocumentEnvelope, Graph, str]],
) -> int:
    if not batch:
        return 0
    dataset = Dataset()
    for _, graph, graph_uri in batch:
        target = dataset.graph(URIRef(graph_uri))
        for triple in graph:
            target.add(triple)
    serialized = dataset.serialize(format="trig", encoding="utf-8")
    assert isinstance(serialized, bytes)
    post_dataset(serialized)
    save_semantic_documents(
        job_id,
        source_system,
        [(document, graph_uri) for document, _, graph_uri in batch],
    )
    return len(batch)


def run_semantic_ingestion(
    content: BinaryIO,
    source_system: str,
    file_name: str,
) -> IngestionJob:
    job = create_ingestion_job(
        source_system,
        file_name,
        "jsonl",
        SEMANTIC_INGESTION_VERSION,
    )
    total = imported = duplicates = quarantined = 0
    batch: list[tuple[SemanticDocumentEnvelope, Graph, str]] = []
    try:
        document_ids, document_hashes = load_semantic_document_keys()
        update_ingestion_job(job.id, "RUNNING")
        update_ingestion_job(job.id, "MAPPING")
        for record_number, raw_line in enumerate(content, start=1):
            if not raw_line.strip():
                continue
            total += 1
            try:
                document, graph = _parse_semantic_line(raw_line)
                if document.document_hash in document_hashes:
                    duplicates += 1
                    continue
                if document.document_id in document_ids:
                    raise SemanticDocumentError(
                        "DOCUMENT_ID_CONFLICT",
                        "Document ID already exists with different content.",
                        _error_record(document.model_dump()),
                    )
            except SemanticDocumentError as exc:
                quarantined += 1
                save_ingestion_error(
                    job.id,
                    record_number,
                    str(exc.raw_record.get("document_id") or "") or None,
                    exc.code,
                    str(exc),
                    exc.raw_record,
                )
                continue

            graph_uri = f"urn:dpp:{document.document_id}"
            batch.append((document, graph, graph_uri))
            document_ids.add(document.document_id)
            document_hashes.add(document.document_hash)
            if len(batch) == BATCH_SIZE:
                imported += _flush_semantic_batch(job.id, source_system, batch)
                batch.clear()

        if total == 0:
            raise IngestionFormatError("The JSONL upload must contain at least one record.")
        imported += _flush_semantic_batch(job.id, source_system, batch)
        final_status: JobStatus
        if quarantined == total:
            final_status = "QUARANTINED"
        elif quarantined:
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
