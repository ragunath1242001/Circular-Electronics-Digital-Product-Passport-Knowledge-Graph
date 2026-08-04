from app.services.observability_service import calculate_quality_score


def test_quality_score_is_reproducible_from_components_and_weights() -> None:
    components = {
        "completeness": 100.0,
        "conformance": 80.0,
        "provenance": 100.0,
        "vocabulary": 100.0,
        "reference_integrity": 50.0,
    }
    weights = {
        "completeness": 0.30,
        "conformance": 0.25,
        "provenance": 0.20,
        "vocabulary": 0.15,
        "reference_integrity": 0.10,
    }

    assert calculate_quality_score(components, weights) == 90.0
