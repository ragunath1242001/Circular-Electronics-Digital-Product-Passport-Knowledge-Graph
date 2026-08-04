from pathlib import Path
from uuid import UUID

from app.schemas.ingestion import SmartphoneRecord
from app.semantic.graph_builder import record_to_graph
from app.semantic.uri_factory import resource_uri, slugify
from app.services.ingestion_service import parse_records, record_hash
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

