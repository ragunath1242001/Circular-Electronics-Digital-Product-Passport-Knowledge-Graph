from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api import dashboard
from app.main import app
from app.schemas.dashboard import TermUsage
from app.schemas.semantic_metrics import SemanticMetric


def test_ecosystem_summary_uses_canonical_metrics(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        dashboard,
        "load_ecosystem_counts",
        lambda: {
            "documents": 10_000,
            "organisations": 20,
            "domains": {"electronics": 7000, "battery": 3000},
            "ontology_versions": {"2.0.0": 8000, "1.0.0": 2000},
            "generated_at": datetime(2026, 8, 15, tzinfo=UTC),
        },
    )
    monkeypatch.setattr(
        dashboard,
        "get_metrics",
        lambda _: [
            SemanticMetric(
                metric_id="MET-001",
                name="Current Ontology Adoption Rate",
                value=0.8,
                numerator=8000,
                denominator=10_000,
                calculation_version="1.0.0",
                calculated_at=datetime(2026, 8, 15, tzinfo=UTC),
            )
        ],
    )

    response = TestClient(app).get("/api/v1/ecosystem/summary")

    assert response.status_code == 200
    assert response.json()["documents"] == 10_000
    assert response.json()["main_metrics"]["MET-001"] == 0.8


def test_static_unknown_term_route_precedes_registry_iri_route(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        dashboard,
        "list_term_usage",
        lambda category, limit, offset: [
            TermUsage(
                term_iri="https://example.org/dpp/unknown",
                category=category,
                occurrences=10,
                documents=8,
                organisations=2,
                domains=["battery"],
                first_seen=datetime(2026, 8, 15, tzinfo=UTC),
                last_seen=datetime(2026, 8, 15, tzinfo=UTC),
            )
        ],
    )

    response = TestClient(app).get("/api/v1/terms/unknown")

    assert response.status_code == 200
    assert response.json()[0]["category"] == "unknown"
