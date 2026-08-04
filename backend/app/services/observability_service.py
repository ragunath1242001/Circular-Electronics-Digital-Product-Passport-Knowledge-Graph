import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from app.core.config import get_settings
from app.db.validation_runs import list_validation_runs
from app.schemas.observability import (
    FilterOptions,
    ObservabilityMetrics,
    RuleFailure,
    SupplierScore,
    TermUsage,
    TrendPoint,
    VersionUsage,
)
from app.services.graph_store import select

PRODUCT_QUERY = """
PREFIX dpp: <https://example.org/dpp/>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?graph ?product ?productIdentifier ?modelNumber ?manufacturer ?manufacturerName
       ?passport ?passportVersion ?ontologyVersion ?supplier ?supplierName ?materialType
       ?origin ?lifecycle
       ?provenance ?carbon ?repairability ?recycling
WHERE {
  GRAPH ?graph {
    ?product a dpp:Smartphone .
    OPTIONAL { ?product dpp:productIdentifier ?productIdentifier }
    OPTIONAL { ?product dpp:modelNumber ?modelNumber }
    OPTIONAL {
      ?product dpp:manufacturedBy ?manufacturer .
      ?manufacturer dct:title ?manufacturerName
    }
    OPTIONAL {
      ?product dpp:hasPassport ?passport .
      ?passport dpp:version ?passportVersion .
      OPTIONAL { ?passport dpp:ontologyVersion ?ontologyVersion }
    }
    OPTIONAL { ?product dpp:hasLifecycleStatus ?lifecycle }
    OPTIONAL { ?product dpp:hasProvenance ?provenance }
    OPTIONAL { ?product dpp:hasCarbonFootprint ?carbon }
    OPTIONAL { ?product dpp:repairabilityScore ?repairability }
    OPTIONAL { ?product dpp:hasRecyclingInstruction ?recycling }
    OPTIONAL {
      ?product dpp:containsComponent ?component .
      ?component dpp:suppliedBy ?supplier .
      ?supplier dct:title ?supplierName
    }
    OPTIONAL {
      ?product dpp:containsComponent ?materialComponent .
      ?materialComponent dpp:containsMaterial ?material .
      ?material dpp:materialType ?materialType .
      OPTIONAL { ?material dpp:originatesFrom ?origin }
    }
  }
  FILTER(STRSTARTS(STR(?graph), "urn:dpp:graph:passport:"))
}
"""
CONTROLLED_MATERIAL_BASE = "https://example.org/dpp/material/"
CONTROLLED_LIFECYCLES = {"https://example.org/dpp/Active", "https://example.org/dpp/Archived"}


@dataclass
class Observation:
    graph: str
    product: str
    product_identifier: str = ""
    model: str = ""
    manufacturer: str = ""
    manufacturer_uri: str = ""
    passport: str = ""
    version: str = "0.0.0"
    ontology_version: str = "Unrecorded"
    lifecycle: str = ""
    provenance: str = ""
    carbon: str = ""
    repairability: str = ""
    recycling: str = ""
    suppliers: set[str] = field(default_factory=set)
    supplier_uris: set[str] = field(default_factory=set)
    materials: set[str] = field(default_factory=set)
    origins: set[str] = field(default_factory=set)


def _version_key(value: str) -> tuple[int, ...]:
    numbers = tuple(int(number) for number in re.findall(r"\d+", value))
    return numbers or (0,)


def _observations(rows: list[dict[str, str]]) -> list[Observation]:
    grouped: dict[tuple[str, str], Observation] = {}
    scalar_fields = {
        "productIdentifier": "product_identifier",
        "modelNumber": "model",
        "manufacturerName": "manufacturer",
        "manufacturer": "manufacturer_uri",
        "passport": "passport",
        "passportVersion": "version",
        "ontologyVersion": "ontology_version",
        "lifecycle": "lifecycle",
        "provenance": "provenance",
        "carbon": "carbon",
        "repairability": "repairability",
        "recycling": "recycling",
    }
    for row in rows:
        key = (row["graph"], row["product"])
        observation = grouped.setdefault(key, Observation(graph=key[0], product=key[1]))
        for source, target in scalar_fields.items():
            if row.get(source):
                setattr(observation, target, row[source])
        if row.get("supplierName"):
            observation.suppliers.add(row["supplierName"])
        if row.get("supplier"):
            observation.supplier_uris.add(row["supplier"])
        if row.get("materialType"):
            observation.materials.add(row["materialType"])
        if row.get("origin"):
            observation.origins.add(row["origin"])

    latest: dict[str, Observation] = {}
    for observation in grouped.values():
        current = latest.get(observation.product)
        if current is None or (_version_key(observation.version), observation.graph) > (
            _version_key(current.version),
            current.graph,
        ):
            latest[observation.product] = observation
    return list(latest.values())


def _percent(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 2) if denominator else 0.0


def calculate_quality_score(
    components: dict[str, float],
    weights: dict[str, float],
) -> float:
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("At least one semantic quality weight must be greater than zero.")
    return round(
        sum(components[name] * weights[name] for name in components) / total_weight,
        2,
    )


def _uri_label(value: str) -> str:
    return value.rstrip("/#").rsplit("/", 1)[-1].rsplit("#", 1)[-1]


def get_metrics(
    manufacturer: str | None = None,
    supplier: str | None = None,
    model: str | None = None,
) -> ObservabilityMetrics:
    # ponytail: aggregate in memory; move to materialized metrics above 10,000 products.
    all_products = _observations(select(PRODUCT_QUERY))
    options = FilterOptions(
        manufacturers=sorted({item.manufacturer for item in all_products if item.manufacturer}),
        suppliers=sorted({name for item in all_products for name in item.suppliers}),
        models=sorted({item.model for item in all_products if item.model}),
    )
    products = [
        item
        for item in all_products
        if (not manufacturer or item.manufacturer.casefold() == manufacturer.casefold())
        and (not supplier or supplier.casefold() in {name.casefold() for name in item.suppliers})
        and (not model or item.model.casefold() == model.casefold())
    ]
    count = len(products)
    mandatory_values = [
        value
        for item in products
        for value in (
            item.product_identifier,
            item.model,
            item.manufacturer,
            item.passport,
            item.carbon,
            item.recycling,
        )
    ]
    completeness = _percent(sum(bool(value) for value in mandatory_values), count * 6)
    provenance = _percent(sum(bool(item.provenance) for item in products), count)
    vocabulary = _percent(
        sum(
            item.lifecycle in CONTROLLED_LIFECYCLES
            and bool(item.materials)
            and all(term.startswith(CONTROLLED_MATERIAL_BASE) for term in item.materials)
            for item in products
        ),
        count,
    )
    references = _percent(
        sum(bool(item.passport and item.manufacturer and item.suppliers) for item in products),
        count,
    )

    reports = list_validation_runs(1000)
    conformance = _percent(sum(report.conforms for report in reports), len(reports))
    settings = get_settings()
    weights = {
        "completeness": settings.quality_weight_completeness,
        "conformance": settings.quality_weight_conformance,
        "provenance": settings.quality_weight_provenance,
        "vocabulary": settings.quality_weight_vocabulary,
        "reference_integrity": settings.quality_weight_reference_integrity,
    }
    components = {
        "completeness": completeness,
        "conformance": conformance,
        "provenance": provenance,
        "vocabulary": vocabulary,
        "reference_integrity": references,
    }

    vocabulary_counts = Counter(
        term for item in products for term in ({item.lifecycle} | item.materials) if term
    )
    versions = Counter(item.ontology_version for item in products)
    supplier_products: dict[str, list[Observation]] = defaultdict(list)
    for item in products:
        for name in item.suppliers:
            supplier_products[name].append(item)

    identity_uris: dict[str, set[str]] = defaultdict(set)
    for item in products:
        if item.manufacturer:
            identity_uris[item.manufacturer.casefold()].add(item.manufacturer_uri)
        for name, uri in zip(sorted(item.suppliers), sorted(item.supplier_uris), strict=False):
            identity_uris[name.casefold()].add(uri)

    cutoff = date.today() - timedelta(days=29)
    trend: dict[date, dict[str, int]] = defaultdict(
        lambda: {"runs": 0, "passed": 0, "violations": 0}
    )
    failures: Counter[str] = Counter()
    for report in reports:
        report_date = report.created_at.date()
        if report_date >= cutoff:
            trend[report_date]["runs"] += 1
            trend[report_date]["passed"] += int(report.conforms)
            trend[report_date]["violations"] += report.violations
        for result in report.results:
            if result.severity == "Violation":
                failures[_uri_label(result.source_shape or result.path or "Unclassified")] += 1

    return ObservabilityMetrics(
        generated_at=datetime.now(UTC),
        applied_filters={
            key: value
            for key, value in {
                "manufacturer": manufacturer,
                "supplier": supplier,
                "model": model,
            }.items()
            if value
        },
        available_filters=options,
        products=count,
        passports=sum(bool(item.passport) for item in products),
        validation_runs=len(reports),
        quality_score=calculate_quality_score(components, weights),
        score_components=components,
        score_weights=weights,
        conformance_rate=conformance,
        supplier_completeness=_percent(sum(bool(item.suppliers) for item in products), count),
        carbon_completeness=_percent(sum(bool(item.carbon) for item in products), count),
        repair_completeness=_percent(sum(bool(item.repairability) for item in products), count),
        recycling_completeness=_percent(
            sum(bool(item.recycling and item.origins) for item in products),
            count,
        ),
        missing_mandatory_fields=sum(not value for value in mandatory_values),
        missing_provenance=sum(not item.provenance for item in products),
        unknown_vocabulary_terms=sum(
            count
            for term, count in vocabulary_counts.items()
            if term not in CONTROLLED_LIFECYCLES and not term.startswith(CONTROLLED_MATERIAL_BASE)
        ),
        deprecated_term_usage=0,
        duplicate_entity_candidates=sum(len(uris) > 1 for uris in identity_uris.values()),
        vocabulary_usage=[
            TermUsage(
                term=_uri_label(term),
                count=term_count,
                controlled=term in CONTROLLED_LIFECYCLES
                or term.startswith(CONTROLLED_MATERIAL_BASE),
            )
            for term, term_count in vocabulary_counts.most_common()
        ],
        ontology_versions=[
            VersionUsage(version=version, products=product_count)
            for version, product_count in sorted(versions.items())
        ],
        supplier_scores=[
            SupplierScore(
                supplier=name,
                products=len(items),
                completeness=_percent(
                    sum(bool(item.materials and item.origins) for item in items),
                    len(items),
                ),
            )
            for name, items in sorted(supplier_products.items())
        ],
        top_failing_rules=[
            RuleFailure(rule=rule, count=failure_count)
            for rule, failure_count in failures.most_common(8)
        ],
        validation_trend=[
            TrendPoint(date=day, **values) for day, values in sorted(trend.items())
        ],
    )
