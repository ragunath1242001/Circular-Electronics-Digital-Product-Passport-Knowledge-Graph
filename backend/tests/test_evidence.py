from datetime import UTC, datetime
from uuid import uuid4

from app.db.evidence import ObservationStats, ShaclEvidence
from app.schemas.evidence import EvidenceUpdate
from app.schemas.semantic_incidents import DetectorType, SemanticIncident
from app.services.evidence_service import candidate_from_incident, candidate_from_shacl


def _incident(detector_type: DetectorType) -> SemanticIncident:
    dimensions = (
        {"term_iri": "https://example.org/concept"}
        if detector_type in {"DET-001", "DET-002", "DET-006"}
        else {"concept_group": "chemistry"}
        if detector_type == "DET-005"
        else {"domain": "battery"}
    )
    return SemanticIncident(
        id=uuid4(),
        detector_type=detector_type,
        severity="warning",
        status="OPEN",
        dimensions=dimensions,
        affected_entities=(
            {"terms": ["https://example.org/chemistry-a", "https://example.org/chemistry-b"]}
            if detector_type == "DET-005"
            else {"domains": ["battery"]}
        ),
        observed_values={"rolling_growth": 0.1} if detector_type == "DET-004" else {},
        baseline={"expected": 0},
        threshold_rule="occurrences >= 10",
        evidence_references=["semantic_observation:1"],
        explanation="Repeated semantic signal.",
        detector_version="1.0.0",
        opened_at=datetime(2026, 8, 14, tzinfo=UTC),
        last_detected_at=datetime(2026, 8, 15, tzinfo=UTC),
    )


def _stats() -> ObservationStats:
    return ObservationStats(
        first_seen=datetime(2026, 8, 14, tzinfo=UTC),
        last_seen=datetime(2026, 8, 15, tzinfo=UTC),
        occurrences=200,
        documents=150,
        organisations=4,
        domains=("battery", "electronics"),
        evidence_references=("semantic_observation:1",),
    )


def test_incidents_become_all_six_human_review_candidate_types() -> None:
    candidates = [
        candidate_from_incident(_incident(detector_type), _stats())
        for detector_type in (
            "DET-001",
            "DET-002",
            "DET-003",
            "DET-004",
            "DET-005",
            "DET-006",
        )
    ]

    assert {item.candidate_type for item in candidates} == {
        "EMERGING_CONCEPT",
        "DEPRECATION_MIGRATION_PROBLEM",
        "VERSION_MIGRATION_FRICTION",
        "DOCUMENTATION_FRICTION",
        "CROSS_SECTOR_MODEL_CONFLICT",
        "MAPPING_NEEDED",
    }
    assert all(item.occurrence_count == 200 for item in candidates)
    assert all(item.organisation_count == 4 for item in candidates)
    assert all(item.evidence_references for item in candidates)
    assert all(item.recommendation.startswith("Review") for item in candidates)
    assert candidates[3].trend == "increasing"


def test_recurring_shacl_failures_become_reviewable_evidence() -> None:
    candidate = candidate_from_shacl(
        ShaclEvidence(
            profile="battery-2.0",
            path="https://example.org/dpp/batteryChemistry",
            component="MinCountConstraintComponent",
            message="Battery chemistry is required.",
            stats=_stats(),
        )
    )

    assert candidate.candidate_type == "SHACL_RULE_FRICTION"
    assert candidate.conformance_impact == 150
    assert candidate.mapping_status == "not_applicable"
    assert candidate.evidence_references == ["semantic_observation:1"]
    assert EvidenceUpdate(annotation=None).model_fields_set == {"annotation"}
