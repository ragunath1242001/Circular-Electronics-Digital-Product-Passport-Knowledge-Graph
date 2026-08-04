from pathlib import Path

from fastapi.testclient import TestClient

from app.api import validation as validation_api
from app.main import app

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
    assert str(saved[0][0].id) == response.json()["id"]
    assert "sh:ValidationReport" in saved[0][1]


def test_invalid_rdf_is_rejected(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(validation_api, "save_validation_run", lambda *_: None)

    response = TestClient(app).post(
        "/api/v1/validation/runs",
        json={"data": "not turtle", "format": "turtle"},
    )

    assert response.status_code == 422
