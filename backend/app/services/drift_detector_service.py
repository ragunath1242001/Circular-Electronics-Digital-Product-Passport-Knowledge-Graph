from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.db.semantic_incidents import (
    DetectorInputs,
    SharePoint,
    TermSignal,
    load_detector_inputs,
    save_incidents,
)
from app.schemas.semantic_incidents import (
    DetectorConfig,
    DetectorRun,
    DetectorType,
    IncidentCandidate,
)
from app.services.semantic_registry import get_registry

CONFIG_PATH = Path(__file__).resolve().parents[3] / "data" / "detectors.json"


@lru_cache
def get_detector_config() -> DetectorConfig:
    try:
        return DetectorConfig.model_validate_json(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise RuntimeError("Detector configuration is unavailable.") from exc


def _share(point: SharePoint) -> float:
    return round(point.numerator / point.denominator, 4) if point.denominator else 0.0


def _term_candidate(
    signal: TermSignal,
    detector_type: DetectorType,
    label: str,
    minimum: int,
    version: str,
) -> IncidentCandidate:
    return IncidentCandidate(
        detector_type=detector_type,
        severity="critical" if signal.occurrences >= 500 else "warning",
        dimensions={"term_iri": signal.term_iri},
        affected_entities={
            "documents": signal.documents,
            "organisations": signal.organisations,
            "domains": list(signal.domains),
        },
        observed_values={"occurrences": signal.occurrences},
        baseline={"expected_occurrences": 0},
        threshold_rule=f"occurrences >= {minimum}",
        evidence_references=[f"semantic_observation:{item}" for item in signal.evidence_ids],
        explanation=f"{label} {signal.term_iri} occurred {signal.occurrences} times.",
        detector_version=version,
    )


def _by_domain(points: tuple[SharePoint, ...]) -> dict[str, list[SharePoint]]:
    grouped: defaultdict[str, list[SharePoint]] = defaultdict(list)
    for point in points:
        grouped[point.domain].append(point)
    return {
        domain: sorted(values, key=lambda item: item.day)
        for domain, values in grouped.items()
    }


def detect_incidents(
    inputs: DetectorInputs,
    config: DetectorConfig | None = None,
) -> list[IncidentCandidate]:
    config = config or get_detector_config()
    candidates = [
        _term_candidate(
            signal,
            "DET-001",
            "Unknown term",
            config.unknown_term_min_occurrences,
            config.detector_version,
        )
        for signal in inputs.unknown_terms
        if signal.occurrences >= config.unknown_term_min_occurrences
    ]
    candidates.extend(
        _term_candidate(
            signal,
            "DET-002",
            "Deprecated term",
            config.deprecated_term_min_occurrences,
            config.detector_version,
        )
        for signal in inputs.deprecated_terms
        if signal.occurrences >= config.deprecated_term_min_occurrences
    )

    for domain, points in _by_domain(inputs.version_shares).items():
        latest = points[-1]
        latest_share = _share(latest)
        recent = points[-config.version_increase_periods :]
        increasing = len(recent) == config.version_increase_periods and all(
            _share(left) < _share(right) for left, right in zip(recent, recent[1:])
        )
        if latest_share <= config.legacy_version_share_threshold and not increasing:
            continue
        candidates.append(
            IncidentCandidate(
                detector_type="DET-003",
                severity="critical"
                if latest_share >= config.legacy_version_share_threshold * 2
                else "warning",
                dimensions={"domain": domain},
                affected_entities={"domains": [domain], "documents": latest.denominator},
                observed_values={
                    "legacy_share": latest_share,
                    "legacy_documents": latest.numerator,
                    "history": [f"{item.day}:{_share(item)}" for item in recent],
                },
                baseline={"legacy_share_threshold": config.legacy_version_share_threshold},
                threshold_rule=(
                    f"legacy share > {config.legacy_version_share_threshold} or increases for "
                    f"{config.version_increase_periods} periods"
                ),
                evidence_references=[f"metric:MET-001?domain={domain}"],
                explanation=f"Legacy ontology share for {domain} is {latest_share:.2%}.",
                detector_version=config.detector_version,
            )
        )

    for domain, points in _by_domain(inputs.custom_shares).items():
        latest = points[-1]
        latest_share = _share(latest)
        recent = points[-config.custom_growth_periods :]
        growth = (
            _share(recent[-1]) - _share(recent[0])
            if len(recent) == config.custom_growth_periods
            else 0.0
        )
        if (
            latest_share <= config.custom_term_share_threshold
            and growth < config.custom_growth_delta
        ):
            continue
        candidates.append(
            IncidentCandidate(
                detector_type="DET-004",
                severity="critical"
                if latest_share >= config.custom_term_share_threshold * 2
                else "warning",
                dimensions={"domain": domain},
                affected_entities={
                    "domains": [domain],
                    "inspected_term_usages": latest.denominator,
                },
                observed_values={"custom_share": latest_share, "rolling_growth": round(growth, 4)},
                baseline={"custom_share_threshold": config.custom_term_share_threshold},
                threshold_rule=(
                    f"custom share > {config.custom_term_share_threshold} or growth >= "
                    f"{config.custom_growth_delta} over {config.custom_growth_periods} periods"
                ),
                evidence_references=[f"metric:MET-003?domain={domain}"],
                explanation=f"Custom vocabulary share for {domain} is {latest_share:.2%}.",
                detector_version=config.detector_version,
            )
        )

    for mapping in get_registry().mappings:
        if mapping.status != "approved":
            continue
        distribution = {
            mapping.source_iri: inputs.term_counts.get(mapping.source_iri, 0),
            mapping.target_iri: inputs.term_counts.get(mapping.target_iri, 0),
        }
        total = sum(distribution.values())
        fragmentation = round(1 - max(distribution.values(), default=0) / total, 4) \
            if total else 0.0
        if fragmentation <= config.fragmentation_threshold:
            continue
        candidates.append(
            IncidentCandidate(
                detector_type="DET-005",
                severity="critical" if fragmentation >= 0.25 else "warning",
                dimensions={"concept_group": mapping.mapping_id},
                affected_entities={"terms": list(distribution)},
                observed_values={
                    "fragmentation_index": fragmentation,
                    "representation_usages": [
                        f"{term}:{count}" for term, count in distribution.items()
                    ],
                },
                baseline={"fragmentation_threshold": config.fragmentation_threshold},
                threshold_rule=f"fragmentation index > {config.fragmentation_threshold}",
                evidence_references=[f"metric:MET-009?group={mapping.mapping_id}"],
                explanation=(
                    f"Concept group {mapping.mapping_id} has fragmentation index "
                    f"{fragmentation:.2%}."
                ),
                detector_version=config.detector_version,
            )
        )

    candidates.extend(
        IncidentCandidate(
            detector_type="DET-006",
            severity="critical" if signal.occurrences >= 500 else "warning",
            dimensions={"term_iri": signal.term_iri},
            affected_entities={
                "documents": signal.documents,
                "organisations": signal.organisations,
                "domains": list(signal.domains),
            },
            observed_values={"occurrences": signal.occurrences},
            baseline={"approved_mapping": False},
            threshold_rule=f"unmapped occurrences >= {config.mapping_gap_min_occurrences}",
            evidence_references=[f"semantic_observation:{item}" for item in signal.evidence_ids],
            explanation=(
                f"Unmapped concept {signal.term_iri} occurred {signal.occurrences} times."
            ),
            detector_version=config.detector_version,
        )
        for signal in inputs.mapping_gaps
        if signal.occurrences >= config.mapping_gap_min_occurrences
    )
    return candidates


def run_detectors() -> DetectorRun:
    config = get_detector_config()
    incidents = save_incidents(
        detect_incidents(load_detector_inputs(), config),
        config.detector_version,
    )
    return DetectorRun(
        detector_version=config.detector_version,
        candidates=len(incidents),
        open_incidents=sum(item.status == "OPEN" for item in incidents),
    )
