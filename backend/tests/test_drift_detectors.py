from datetime import date

from app.db.semantic_incidents import DetectorInputs, SharePoint, TermSignal
from app.services.drift_detector_service import detect_incidents


def _term(term_iri: str, occurrences: int) -> TermSignal:
    return TermSignal(
        term_iri=term_iri,
        occurrences=occurrences,
        documents=occurrences,
        organisations=2,
        domains=("battery",),
        evidence_ids=(1, 2),
    )


def test_all_six_deterministic_detectors_emit_structured_incidents() -> None:
    inputs = DetectorInputs(
        unknown_terms=(_term("https://example.org/dpp/unknown", 10),),
        deprecated_terms=(_term("https://example.org/dpp/chemistry", 12),),
        version_shares=(
            SharePoint(
                domain="battery",
                day=date(2026, 8, 14),
                numerator=20,
                denominator=100,
            ),
        ),
        custom_shares=(
            SharePoint(
                domain="battery",
                day=date(2026, 8, 14),
                numerator=1,
                denominator=100,
            ),
        ),
        mapping_gaps=(_term("https://external.example/vocab/unmapped", 60),),
        term_counts={
            "https://example.org/dpp/chemistry": 20,
            "https://example.org/dpp/batteryChemistry": 80,
        },
    )

    incidents = detect_incidents(inputs)

    assert {item.detector_type for item in incidents} == {
        "DET-001",
        "DET-002",
        "DET-003",
        "DET-004",
        "DET-005",
        "DET-006",
    }
    assert all(item.threshold_rule for item in incidents)
    assert all(item.evidence_references for item in incidents)
    assert all(item.explanation for item in incidents)
    by_type = {item.detector_type: item for item in incidents}
    assert by_type["DET-003"].affected_entities["documents"] == 100
    assert by_type["DET-004"].affected_entities["inspected_term_usages"] == 100
