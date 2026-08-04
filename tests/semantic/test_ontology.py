from scripts.validate_ontology import validate


def test_ontology_foundation() -> None:
    summary = validate()

    assert summary["ontology_modules"] == 7
    assert summary["example_graphs"] == 1
    assert summary["competency_queries"] == 20
