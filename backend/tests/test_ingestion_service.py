import io
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.schemas.ingestion import IngestionJob, SmartphoneRecord
from app.semantic.graph_builder import record_to_graph
from app.semantic.uri_factory import resource_uri, slugify
from app.services import ingestion_service
from app.services.ingestion_service import parse_records, record_hash, semantic_document_hash
from app.services.validation_service import validate_data

ROOT = Path(__file__).resolve().parents[2]


def test_seed_csv_maps_to_a_conformant_graph() -> None:
    content = (ROOT / "data" / "seed" / "smartphones.csv").read_text(encoding="utf-8")
    records = parse_records(content, "csv")

    graph = record_to_graph(
        SmartphoneRecord.model_validate(records[0]),
        "test-seed",
        UUID("00000000-0000-0000-0000-000000000001"),
    )

    assert len(records) == 3
    assert validate_data(str(graph.serialize(format="turtle"))).report.conforms


def test_json_and_hashing_are_deterministic() -> None:
    content = (ROOT / "data" / "seed" / "smartphones.json").read_text(encoding="utf-8")
    record = parse_records(content, "json")[0]

    assert record_hash(record) == record_hash(dict(reversed(list(record.items()))))


def test_uri_generation_normalizes_names() -> None:
    assert slugify("Éco Devices  BV") == "eco-devices-bv"
    assert str(resource_uri("Product", "CFX 2")) == "https://example.org/dpp/resource/product/cfx-2"


def test_jsonl_ingestion_is_idempotent_and_isolates_malformed_lines(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    payload = {
        "@context": {"dpp": "https://example.org/dpp/"},
        "@id": "https://example.org/dpp/synthetic/passport/dpp-test",
        "@type": "dpp:DigitalProductPassport",
    }
    envelope = {
        "document_id": "dpp-test",
        "external_identifier": "PRODUCT-TEST",
        "organisation_id": "org-test",
        "domain": "electronics",
        "semantic_profile_id": "electronics-2.0",
        "declared_ontology_version": "2.0.0",
        "document_hash": semantic_document_hash(payload),
        "payload": payload,
    }
    line = json.dumps(envelope).encode() + b"\n"
    job = IngestionJob(
        id=uuid4(),
        source_system="test",
        file_name="test.jsonl",
        data_format="jsonl",
        mapping_version="semantic-jsonld-1.0",
        status="PENDING",
        created_at=datetime.now(UTC),
    )
    stored: list[object] = []
    errors: list[str] = []
    datasets: list[bytes] = []

    monkeypatch.setattr(ingestion_service, "create_ingestion_job", lambda *_: job)
    monkeypatch.setattr(ingestion_service, "load_semantic_document_keys", lambda: (set(), set()))
    monkeypatch.setattr(
        ingestion_service,
        "update_ingestion_job",
        lambda _, status, total_records=0, imported_records=0, duplicate_records=0,
        quarantined_records=0, error_message=None: job.model_copy(
            update={
                "status": status,
                "total_records": total_records,
                "imported_records": imported_records,
                "duplicate_records": duplicate_records,
                "quarantined_records": quarantined_records,
                "error_message": error_message,
            }
        ),
    )
    monkeypatch.setattr(ingestion_service, "post_dataset", datasets.append)
    monkeypatch.setattr(
        ingestion_service,
        "save_semantic_documents",
        lambda _, __, documents: stored.extend(documents),
    )
    monkeypatch.setattr(
        ingestion_service,
        "save_ingestion_error",
        lambda _, __, ___, code, message, raw: errors.append(code),
    )

    result = ingestion_service.run_semantic_ingestion(
        io.BytesIO(line + line + b"{invalid}\n"),
        "test",
        "test.jsonl",
    )

    assert result.status == "COMPLETED_WITH_WARNINGS"
    assert (result.total_records, result.imported_records) == (3, 1)
    assert (result.duplicate_records, result.quarantined_records) == (1, 1)
    assert len(stored) == len(datasets) == 1
    assert b"urn:dpp:dpp-test" in datasets[0]
    assert errors == ["JSONL_PARSE_FAILED"]
