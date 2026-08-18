from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from rdflib import RDF, RDFS, Graph, Namespace, URIRef

from app.db.semantic_metrics import MetricInputs, list_metric_buckets, load_metric_inputs
from app.schemas.semantic_metrics import (
    MetricBreakdown,
    MetricExplanation,
    MetricFilters,
    MetricId,
    SemanticMetric,
)
from app.services.semantic_registry import get_registry

ONTOLOGY_ROOT = Path(__file__).resolve().parents[3] / "ontology"
SH = Namespace("http://www.w3.org/ns/shacl#")
CALCULATION_VERSION = "1.0.0"

EXPLANATIONS: dict[MetricId, MetricExplanation] = {
    "MET-001": MetricExplanation(
        metric_id="MET-001",
        name="Current Ontology Adoption Rate",
        purpose="Measure adoption of the designated current ontology version.",
        formula="documents on current version / documents with a resolvable version",
        edge_cases=["Unresolved versions are reported separately."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-002": MetricExplanation(
        metric_id="MET-002",
        name="Vocabulary Reuse Rate",
        purpose="Measure reuse of registered and approved external terms.",
        formula="(standard + approved external usages) / all classified term usages",
        edge_cases=["Returns null when no terms were classified."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-003": MetricExplanation(
        metric_id="MET-003",
        name="Custom Term Ratio",
        purpose="Measure reliance on organisation-specific vocabulary.",
        formula="custom term usages / all classified term usages",
        edge_cases=["Returns null when no terms were classified."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-004": MetricExplanation(
        metric_id="MET-004",
        name="Unknown Term Ratio",
        purpose="Measure unregistered terms inside known ontology namespaces.",
        formula="unknown term usages / all semantic term usages inspected",
        edge_cases=["Returns null when no terms were inspected."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-005": MetricExplanation(
        metric_id="MET-005",
        name="DPP SHACL Conformance Rate",
        purpose="Measure documents with no SHACL violations.",
        formula="validated documents with zero violations / validated documents",
        edge_cases=["Warnings are reported but do not fail conformance."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-006": MetricExplanation(
        metric_id="MET-006",
        name="Constraint Conformance Rate",
        purpose="Measure conformance for each evaluated profile constraint.",
        formula="evaluations without violation / constraint evaluations",
        edge_cases=["Constraints with no target nodes return null."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-007": MetricExplanation(
        metric_id="MET-007",
        name="Version Consistency",
        purpose="Show concentration on the modal and current ontology versions.",
        formula="documents on modal version / documents with an observed version",
        edge_cases=["The full distribution is always returned beside the scalar."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-008": MetricExplanation(
        metric_id="MET-008",
        name="Mapping Coverage",
        purpose="Measure coverage of concepts classified as requiring a mapping.",
        formula="distinct mapped concepts / distinct concepts emitted as mapped or missing",
        edge_cases=["The Phase 5 mapping classification defines the denominator."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-009": MetricExplanation(
        metric_id="MET-009",
        name="Semantic Fragmentation Index",
        purpose="Measure representation diversity inside approved mapping groups.",
        formula="1 - dominant representation usages / all group representation usages",
        edge_cases=["Approved registry mappings define concept groups; empty groups return null."],
        calculation_version=CALCULATION_VERSION,
    ),
    "MET-010": MetricExplanation(
        metric_id="MET-010",
        name="Deprecated Usage Rate",
        purpose="Measure deprecated vocabulary use within the registered model.",
        formula="deprecated term usages / (standard + deprecated term usages)",
        edge_cases=["Approved external and custom terms are outside the denominator."],
        calculation_version=CALCULATION_VERSION,
    ),
}


@dataclass(frozen=True)
class ConstraintSpec:
    profile: str
    target_class: str
    path: str | None
    component: str
    message: str


CONSTRAINT_COMPONENTS = {
    SH.minCount: SH.MinCountConstraintComponent,
    SH.maxCount: SH.MaxCountConstraintComponent,
    SH.datatype: SH.DatatypeConstraintComponent,
    SH["class"]: SH.ClassConstraintComponent,
    SH.minInclusive: SH.MinInclusiveConstraintComponent,
    SH.maxInclusive: SH.MaxInclusiveConstraintComponent,
    SH.minExclusive: SH.MinExclusiveConstraintComponent,
    SH.hasValue: SH.HasValueConstraintComponent,
    SH.qualifiedMinCount: SH.QualifiedMinCountConstraintComponent,
    SH.node: SH.NodeConstraintComponent,
    SH["or"]: SH.OrConstraintComponent,
    SH.lessThan: SH.LessThanConstraintComponent,
}


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


@lru_cache
def _ontology_graph() -> Graph:
    graph = Graph()
    for path in sorted((ONTOLOGY_ROOT / "core").glob("*.ttl")):
        graph.parse(path, format="turtle")
    return graph


@lru_cache
def _constraint_catalog() -> tuple[ConstraintSpec, ...]:
    constraints: set[ConstraintSpec] = set()
    for profile in get_registry().profiles:
        graph = Graph()
        for relative_path in profile.shape_paths:
            graph.parse(ONTOLOGY_ROOT / relative_path, format="turtle")
        for node_shape in graph.subjects(RDF.type, SH.NodeShape):
            for target in graph.objects(node_shape, SH.targetClass):
                if not isinstance(target, URIRef):
                    continue
                shapes = [node_shape, *graph.objects(node_shape, SH.property)]
                for shape in shapes:
                    path = graph.value(shape, SH.path)
                    message = str(graph.value(shape, SH.message) or "Validation failed.")
                    for predicate, component in CONSTRAINT_COMPONENTS.items():
                        if graph.value(shape, predicate) is not None:
                            constraints.add(
                                ConstraintSpec(
                                    profile=profile.id,
                                    target_class=str(target),
                                    path=str(path) if path is not None else None,
                                    component=str(component),
                                    message=message,
                                )
                            )
    return tuple(sorted(constraints, key=lambda item: repr(item)))


def _constraint_key(
    profile: str,
    path: str | None,
    component: str,
    message: str,
) -> tuple[str, str | None, str, str]:
    return profile, path, component, message


def _constraint_breakdown(inputs: MetricInputs) -> list[MetricBreakdown]:
    violations = {
        _constraint_key(item.profile, item.path, item.component, item.message): item
        for item in inputs.constraint_violations
    }
    ontology = _ontology_graph()
    breakdown: list[MetricBreakdown] = []
    matched: set[tuple[str, str | None, str, str]] = set()
    for constraint in _constraint_catalog():
        key = _constraint_key(
            constraint.profile,
            constraint.path,
            constraint.component,
            constraint.message,
        )
        matched.add(key)
        classes = {constraint.target_class}
        classes.update(str(item) for item in ontology.transitive_subjects(
            RDFS.subClassOf, URIRef(constraint.target_class)
        ))
        documents: set[str] = set()
        for class_iri in classes:
            documents.update(inputs.class_documents.get((constraint.profile, class_iri), ()))
        violated = violations.get(key)
        violation_count = violated.violations if violated else 0
        evaluated = max(len(documents), violation_count)
        identifier = sha256("\x1f".join(str(item or "") for item in key).encode()).hexdigest()[:16]
        breakdown.append(
            MetricBreakdown(
                key=identifier,
                value=_ratio(evaluated - violation_count, evaluated),
                numerator=evaluated - violation_count,
                denominator=evaluated,
                components={"violations": violation_count},
                metadata={
                    "profile": constraint.profile,
                    "target_class": constraint.target_class,
                    "path": constraint.path or "",
                    "constraint_component": constraint.component,
                    "message": constraint.message,
                },
            )
        )

    # ponytail: unmatched plugin constraints use the profile denominator; persist
    # explicit evaluation events if optional target classes become common.
    for key, violation in violations.items():
        if key in matched:
            continue
        evaluated = max(inputs.profile_validations.get(violation.profile, 0), violation.violations)
        identifier = sha256("\x1f".join(str(item or "") for item in key).encode()).hexdigest()[:16]
        breakdown.append(
            MetricBreakdown(
                key=identifier,
                value=_ratio(evaluated - violation.violations, evaluated),
                numerator=evaluated - violation.violations,
                denominator=evaluated,
                components={"violations": violation.violations},
                metadata={
                    "profile": violation.profile,
                    "path": violation.path or "",
                    "constraint_component": violation.component,
                    "message": violation.message,
                },
            )
        )
    return sorted(breakdown, key=lambda item: item.key)


def calculate_metrics(inputs: MetricInputs) -> list[SemanticMetric]:
    now = datetime.now(UTC)
    categories = inputs.term_categories
    term_total = sum(categories.values())
    resolved_versions = sum(
        item.documents for item in inputs.versions if item.category != "unknown"
    )
    current_versions = sum(
        item.documents for item in inputs.versions if item.category == "standard"
    )
    unresolved_versions = sum(
        item.documents for item in inputs.versions if item.category == "unknown"
    )
    version_distribution: dict[str, int] = {}
    for item in inputs.versions:
        version_distribution[item.version] = (
            version_distribution.get(item.version, 0) + item.documents
        )
    version_total = sum(version_distribution.values())
    modal_count = max(version_distribution.values(), default=0)
    mapped = sum(inputs.mapping_terms.values())
    mappable = len(inputs.mapping_terms)

    constraints = _constraint_breakdown(inputs)
    version_breakdown = [
        MetricBreakdown(
            key=version,
            value=_ratio(count, version_total),
            numerator=count,
            denominator=version_total,
        )
        for version, count in sorted(version_distribution.items())
    ]
    fragmentation = []
    for mapping in get_registry().mappings:
        if mapping.status != "approved":
            continue
        distribution = {
            mapping.source_iri: inputs.term_counts.get(mapping.source_iri, 0),
            mapping.target_iri: inputs.term_counts.get(mapping.target_iri, 0),
        }
        total = sum(distribution.values())
        dominant = max(distribution.values(), default=0)
        fragmentation.append(
            MetricBreakdown(
                key=mapping.mapping_id,
                value=_ratio(total - dominant, total),
                numerator=total - dominant,
                denominator=total,
                components=distribution,
            )
        )

    def metric(
        metric_id: MetricId,
        value: float | None,
        numerator: int | None,
        denominator: int | None,
        components: dict[str, int] | None = None,
        breakdown: list[MetricBreakdown] | None = None,
    ) -> SemanticMetric:
        return SemanticMetric(
            metric_id=metric_id,
            name=EXPLANATIONS[metric_id].name,
            value=value,
            numerator=numerator,
            denominator=denominator,
            components=components or {},
            breakdown=breakdown or [],
            calculation_version=CALCULATION_VERSION,
            calculated_at=now,
        )

    registered = categories.get("standard", 0) + categories.get("deprecated", 0)
    return [
        metric(
            "MET-001",
            _ratio(current_versions, resolved_versions),
            current_versions,
            resolved_versions,
            {"unresolved_versions": unresolved_versions},
        ),
        metric(
            "MET-002",
            _ratio(
                categories.get("standard", 0) + categories.get("external_approved", 0),
                term_total,
            ),
            categories.get("standard", 0) + categories.get("external_approved", 0),
            term_total,
            categories,
        ),
        metric(
            "MET-003",
            _ratio(categories.get("custom", 0), term_total),
            categories.get("custom", 0),
            term_total,
        ),
        metric(
            "MET-004",
            _ratio(categories.get("unknown", 0), term_total),
            categories.get("unknown", 0),
            term_total,
        ),
        metric(
            "MET-005",
            _ratio(inputs.conforming, inputs.validated),
            inputs.conforming,
            inputs.validated,
            {"warnings": inputs.warnings},
        ),
        metric("MET-006", None, None, None, breakdown=constraints),
        metric(
            "MET-007",
            _ratio(modal_count, version_total),
            modal_count,
            version_total,
            {"current_documents": current_versions, "modal_documents": modal_count},
            version_breakdown,
        ),
        metric(
            "MET-008",
            _ratio(mapped, mappable),
            mapped,
            mappable,
            {"unmapped_concepts": mappable - mapped},
        ),
        metric("MET-009", None, None, None, breakdown=fragmentation),
        metric(
            "MET-010",
            _ratio(categories.get("deprecated", 0), registered),
            categories.get("deprecated", 0),
            registered,
        ),
    ]


def get_metrics(filters: MetricFilters, metric_id: MetricId | None = None) -> list[SemanticMetric]:
    if filters.from_date and filters.to_date and filters.from_date > filters.to_date:
        raise ValueError("from must be on or before to.")
    if filters.granularity is None:
        metrics = calculate_metrics(load_metric_inputs(filters))
    else:
        # ponytail: one aggregate query set per bucket; persist snapshots when
        # dashboard history regularly spans more than 90 buckets.
        metrics = []
        for bucket_start in list_metric_buckets(filters):
            if filters.granularity == "day":
                bucket_end = bucket_start
            elif filters.granularity == "week":
                bucket_end = bucket_start + timedelta(days=6)
            else:
                bucket_end = bucket_start.replace(
                    day=monthrange(bucket_start.year, bucket_start.month)[1]
                )
            bucket_from = (
                filters.from_date
                if filters.from_date and filters.from_date > bucket_start
                else bucket_start
            )
            bucket_to = (
                filters.to_date
                if filters.to_date and filters.to_date < bucket_end
                else bucket_end
            )
            bucket_filters = filters.model_copy(
                update={
                    "from_date": bucket_from,
                    "to_date": bucket_to,
                    "granularity": None,
                }
            )
            metrics.extend(
                item.model_copy(update={"bucket_start": bucket_start})
                for item in calculate_metrics(load_metric_inputs(bucket_filters))
            )
    return [item for item in metrics if metric_id is None or item.metric_id == metric_id]


def get_explanation(metric_id: MetricId) -> MetricExplanation:
    return EXPLANATIONS[metric_id]
