import json
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.db.evidence import (
    ObservationStats,
    ShaclEvidence,
    load_incident_stats,
    load_shacl_evidence,
    save_evidence,
)
from app.db.semantic_incidents import list_incidents
from app.schemas.evidence import (
    EvidenceCandidateDraft,
    EvidenceCandidateType,
    EvidenceRun,
    MappingStatus,
)
from app.schemas.semantic_incidents import DetectorType, SemanticIncident

EVIDENCE_VERSION = "1.0.0"
TYPE_BY_DETECTOR: dict[DetectorType, EvidenceCandidateType] = {
    "DET-001": "EMERGING_CONCEPT",
    "DET-002": "DEPRECATION_MIGRATION_PROBLEM",
    "DET-003": "VERSION_MIGRATION_FRICTION",
    "DET-004": "DOCUMENTATION_FRICTION",
    "DET-005": "CROSS_SECTOR_MODEL_CONFLICT",
    "DET-006": "MAPPING_NEEDED",
}


def _key(candidate_type: EvidenceCandidateType, dimensions: object) -> str:
    return sha256(
        f"{EVIDENCE_VERSION}\x1f{candidate_type}\x1f"
        f"{json.dumps(dimensions, sort_keys=True)}".encode()
    ).hexdigest()


def _days(first_seen: datetime, last_seen: datetime) -> int:
    return max((last_seen.date() - first_seen.date()).days + 1, 1)


def _concepts(incident: SemanticIncident) -> list[str]:
    if "term_iri" in incident.dimensions:
        return [str(incident.dimensions["term_iri"])]
    terms = incident.affected_entities.get("terms")
    if isinstance(terms, list):
        return terms
    if "concept_group" in incident.dimensions:
        return [str(incident.dimensions["concept_group"])]
    return [f"domain:{incident.dimensions['domain']}"]


def candidate_from_incident(
    incident: SemanticIncident,
    stats: ObservationStats,
) -> EvidenceCandidateDraft:
    candidate_type = TYPE_BY_DETECTOR[incident.detector_type]
    key = _key(candidate_type, incident.dimensions)
    growth = incident.observed_values.get("rolling_growth")
    growth_rate = float(growth) if isinstance(growth, int | float) else None
    mapping_status: MappingStatus = "not_applicable"
    if incident.detector_type == "DET-006":
        mapping_status = "missing"
    elif incident.detector_type == "DET-005":
        mapping_status = "approved"
    label = {
        "DET-001": "Recurring unknown concept",
        "DET-002": "Deprecated concept still in use",
        "DET-003": "Legacy ontology version adoption",
        "DET-004": "Custom vocabulary documentation friction",
        "DET-005": "Cross-sector representation conflict",
        "DET-006": "External concept needs a mapping",
    }[incident.detector_type]
    return EvidenceCandidateDraft(
        id=uuid5(NAMESPACE_URL, key),
        candidate_key=key,
        candidate_type=candidate_type,
        label=f"{label}: {_concepts(incident)[0]}",
        affected_concepts=_concepts(incident),
        first_seen=stats.first_seen,
        last_seen=stats.last_seen,
        occurrence_count=stats.occurrences,
        organisation_count=stats.organisations,
        domain_count=len(stats.domains),
        trend=(
            "increasing"
            if growth_rate is not None and growth_rate > 0
            else "insufficient_history"
        ),
        growth_rate=growth_rate,
        persistence_days=_days(stats.first_seen, stats.last_seen),
        mapping_status=mapping_status,
        conformance_impact=0,
        metrics={
            "documents": stats.documents,
            "detector_type": incident.detector_type,
            "severity": incident.severity,
            "threshold_rule": incident.threshold_rule,
        },
        recommendation=(
            "Review this recurring evidence with domain experts before proposing any "
            "mapping, documentation, profile, or ontology change."
        ),
        source_incident_id=incident.id,
        evidence_references=[f"semantic_incident:{incident.id}", *stats.evidence_references],
        evidence_version=EVIDENCE_VERSION,
    )


def candidate_from_shacl(source: ShaclEvidence) -> EvidenceCandidateDraft:
    dimensions = {
        "profile": source.profile,
        "path": source.path,
        "component": source.component,
        "message": source.message,
    }
    key = _key("SHACL_RULE_FRICTION", dimensions)
    stats = source.stats
    concept = source.path or source.component
    return EvidenceCandidateDraft(
        id=uuid5(NAMESPACE_URL, key),
        candidate_key=key,
        candidate_type="SHACL_RULE_FRICTION",
        label=f"Recurring SHACL rule friction: {concept}",
        affected_concepts=[concept],
        first_seen=stats.first_seen,
        last_seen=stats.last_seen,
        occurrence_count=stats.occurrences,
        organisation_count=stats.organisations,
        domain_count=len(stats.domains),
        trend="insufficient_history",
        persistence_days=_days(stats.first_seen, stats.last_seen),
        mapping_status="not_applicable",
        conformance_impact=stats.documents,
        metrics={
            "documents": stats.documents,
            "profile": source.profile,
            "constraint_component": source.component,
            "message": source.message,
        },
        recommendation=(
            "Review the recurring validation failures with profile maintainers before changing "
            "the SHACL rule or its documentation."
        ),
        evidence_references=list(stats.evidence_references),
        evidence_version=EVIDENCE_VERSION,
    )


def run_evidence_generation() -> EvidenceRun:
    incidents = list_incidents(None, None, "OPEN", 500, 0)
    stats = load_incident_stats(incidents)
    drafts = [
        candidate_from_incident(incident, stats[incident.id])
        for incident in incidents
        if incident.id in stats
    ]
    drafts.extend(candidate_from_shacl(item) for item in load_shacl_evidence())
    stored = save_evidence(drafts)
    return EvidenceRun(evidence_version=EVIDENCE_VERSION, candidates=len(stored))
