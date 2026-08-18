from pathlib import Path

from fastapi.testclient import TestClient

from app.api import validation as validation_api
from app.main import app
from app.schemas.validation import StoredSemanticDocument
from app.services import validation_service

ROOT = Path(__file__).resolve().parents[2]


def test_validation_run_is_saved(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    saved = []
    monkeypatch.setattr(
        validation_api,
        "save_validation_run",
        lambda report, report_turtle: saved.append((report, report_turtle)),
    )
    data = (ROOT / "ontology" / "fixtures" / "invalid-phone.ttl").read_text(encoding="utf-8")

    response = TestClient(app).post(
        "/api/v1/validation/runs",
        json={"data": data, "format": "turtle"},
    )

    assert response.status_code == 201
    assert response.json()["conforms"] is False
    assert response.json()["results"][0]["constraint_component"]
    assert str(saved[0][0].id) == response.json()["id"]
    assert "sh:ValidationReport" in saved[0][1]


def test_invalid_rdf_is_rejected(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(validation_api, "save_validation_run", lambda *_: None)

    response = TestClient(app).post(
        "/api/v1/validation/runs",
        json={"data": "not turtle", "format": "turtle"},
    )

    assert response.status_code == 422


def test_pending_documents_use_the_registered_profile(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    saved = []
    document = StoredSemanticDocument(
        document_id="test-document",
        organisation_id="test-organisation",
        domain="electronics",
        semantic_profile_id="electronics-2.0",
        declared_ontology_version="2.0.0",
        graph_uri="urn:dpp:test-document",
    )
    data = (ROOT / "ontology" / "fixtures" / "invalid-phone.ttl").read_bytes()
    monkeypatch.setattr(validation_service, "list_pending_documents", lambda _: [document])
    monkeypatch.setattr(validation_service, "get_graph", lambda _: data)
    monkeypatch.setattr(validation_service, "save_document_validations", saved.extend)

    result = validation_service.validate_pending_documents(1)

    assert result.documents == 1
    assert result.nonconforming == 1
    assert result.observations > 0
    assert saved[0].document.semantic_profile_id == "electronics-2.0"
    assert saved[0].report.results[0].constraint_component
