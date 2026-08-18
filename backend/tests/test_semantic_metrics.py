from fastapi.testclient import TestClient

from app.db.semantic_metrics import ConstraintViolation, MetricInputs, VersionStat
from app.main import app
from app.services.semantic_metrics_service import calculate_metrics


def test_all_documented_metric_formulas() -> None:
    inputs = MetricInputs(
        versions=(
            VersionStat(version="2.0.0", category="standard", documents=7),
            VersionStat(version="1.1.0", category="deprecated", documents=2),
            VersionStat(version="unresolved", category="unknown", documents=1),
        ),
        term_categories={
            "standard": 80,
            "external_approved": 10,
            "custom": 5,
            "unknown": 3,
            "deprecated": 2,
        },
        term_counts={
            "https://example.org/dpp/chemistry": 20,
            "https://example.org/dpp/batteryChemistry": 80,
        },
        mapping_terms={"mapped": True, "missing": False},
        validated=10,
        conforming=8,
        warnings=2,
        profile_validations={"battery-2.0": 10},
        class_documents={
            ("battery-2.0", "https://example.org/dpp/Battery"): frozenset(
                f"document-{index}" for index in range(10)
            )
        },
        constraint_violations=(
            ConstraintViolation(
                profile="battery-2.0",
                path="https://example.org/dpp/batteryChemistry",
                component="http://www.w3.org/ns/shacl#MinCountConstraintComponent",
                message="A battery must declare its chemistry.",
                violations=2,
            ),
        ),
    )

    metrics = {item.metric_id: item for item in calculate_metrics(inputs)}

    assert len(metrics) == 10
    assert metrics["MET-001"].value == 0.7778
    assert metrics["MET-002"].value == 0.9
    assert metrics["MET-003"].value == 0.05
    assert metrics["MET-004"].value == 0.03
    assert metrics["MET-005"].value == 0.8
    constraint = next(
        item for item in metrics["MET-006"].breakdown if item.components["violations"] == 2
    )
    assert (constraint.value, constraint.numerator, constraint.denominator) == (0.8, 8, 10)
    assert metrics["MET-007"].value == 0.7
    assert metrics["MET-008"].value == 0.5
    assert metrics["MET-009"].breakdown[0].value == 0.2
    assert metrics["MET-010"].value == 0.0244


def test_every_metric_has_an_explanation() -> None:
    client = TestClient(app)
    for number in range(1, 11):
        response = client.get(f"/api/v1/metrics/MET-{number:03d}/explain")
        assert response.status_code == 200
        assert response.json()["formula"]
        assert response.json()["edge_cases"]
