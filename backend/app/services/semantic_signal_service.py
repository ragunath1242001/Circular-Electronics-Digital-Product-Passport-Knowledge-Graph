from collections import Counter
from datetime import UTC, datetime
from urllib.parse import urlsplit

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from app.db.semantic_observations import list_pending_documents, save_observations
from app.schemas.semantic_registry import SemanticProfile
from app.schemas.semantic_signals import (
    ObservationType,
    SemanticObservation,
    SignalBatch,
    TermCategory,
)
from app.schemas.validation import StoredSemanticDocument
from app.services.graph_store import get_graph
from app.services.semantic_registry import SemanticRegistry, get_registry

BUILTIN_NAMESPACES = (str(RDF), str(RDFS), str(OWL), str(XSD))


def _namespace(iri: str) -> str:
    boundary = max(iri.rfind("#"), iri.rfind("/"))
    return iri[: boundary + 1] if boundary >= 0 else iri


def _organisation_owned(term: str, organisation_id: str) -> bool:
    hostname = urlsplit(term).hostname
    return hostname is not None and organisation_id.lower() in hostname.lower().split(".")


def _category(
    term: str,
    profile: SemanticProfile,
    registry: SemanticRegistry,
) -> TermCategory:
    registered = next((item for item in registry.terms if item.iri == term), None)
    if registered:
        return "deprecated" if registered.status == "deprecated" else "standard"
    namespace = _namespace(term)
    if any(
        namespace.startswith(item)
        for ontology in registry.ontologies
        for item in ontology.namespaces
    ):
        return "unknown"
    if any(
        namespace.startswith(item)
        for item in (*profile.accepted_namespaces, *BUILTIN_NAMESPACES)
    ):
        return "external_approved"
    return "custom"


def collect_signals(
    document: StoredSemanticDocument,
    graph_data: bytes,
    registry: SemanticRegistry | None = None,
) -> list[SemanticObservation]:
    registry = registry or get_registry()
    profile = next(
        (
            item
            for item in registry.profiles
            if item.id == document.semantic_profile_id and item.domain == document.domain
        ),
        None,
    )
    if profile is None:
        raise ValueError(
            f"Unknown semantic profile {document.semantic_profile_id!r} for {document.domain}."
        )

    graph = Graph().parse(data=graph_data.decode("utf-8"), format="turtle")
    classes = Counter(
        str(value)
        for value in graph.objects(None, RDF.type)
        if isinstance(value, URIRef)
    )
    properties = Counter(
        str(predicate) for predicate in graph.predicates() if isinstance(predicate, URIRef)
    )
    terms = classes + properties
    categories = {term: _category(term, profile, registry) for term in terms}
    namespaces: Counter[str] = Counter()
    for term, count in terms.items():
        namespaces[_namespace(term)] += count

    observed_at = datetime.now(UTC)
    version = next(
        (
            item
            for item in registry.versions
            if item.ontology_id == "products"
            and item.version == document.declared_ontology_version
        ),
        None,
    )
    observations = [
        SemanticObservation(
            document_id=document.document_id,
            observed_at=observed_at,
            observation_type="ontology_version",
            term_iri=version.version_iri if version else None,
            category=("deprecated" if version and version.status == "deprecated" else "standard")
            if version
            else "unknown",
            ontology_version=document.declared_ontology_version,
        )
    ]
    usage_groups: tuple[tuple[ObservationType, Counter[str]], ...] = (
        ("class_usage", classes),
        ("property_usage", properties),
    )
    observations.extend(
        SemanticObservation(
            document_id=document.document_id,
            observed_at=observed_at,
            observation_type=observation_type,
            term_iri=term,
            namespace=_namespace(term),
            ontology_version=document.declared_ontology_version,
            occurrence_count=count,
        )
        for observation_type, usages in usage_groups
        for term, count in sorted(usages.items())
    )
    observations.extend(
        SemanticObservation(
            document_id=document.document_id,
            observed_at=observed_at,
            observation_type="namespace_usage",
            namespace=namespace,
            ontology_version=document.declared_ontology_version,
            occurrence_count=count,
        )
        for namespace, count in sorted(namespaces.items())
    )
    observations.extend(
        SemanticObservation(
            document_id=document.document_id,
            observed_at=observed_at,
            observation_type="term_classification",
            term_iri=term,
            namespace=_namespace(term),
            category=category,
            ontology_version=document.declared_ontology_version,
            occurrence_count=terms[term],
        )
        for term, category in sorted(categories.items())
    )

    approved_mappings = {
        item.source_iri: item for item in registry.mappings if item.status == "approved"
    }
    observations.extend(
        SemanticObservation(
            document_id=document.document_id,
            observed_at=observed_at,
            observation_type="mapping_used"
            if term in approved_mappings
            else "mapping_missing",
            term_iri=term,
            namespace=_namespace(term),
            ontology_version=document.declared_ontology_version,
            occurrence_count=terms[term],
        )
        for term, category in sorted(categories.items())
        if term in approved_mappings
        or (category == "custom" and not _organisation_owned(term, document.organisation_id))
    )
    return observations


def collect_pending_documents(limit: int) -> SignalBatch:
    registry = get_registry()
    observations: list[SemanticObservation] = []
    documents = list_pending_documents(limit)
    for document in documents:
        observations.extend(collect_signals(document, get_graph(document.graph_uri), registry))
    save_observations(observations)
    return SignalBatch(
        documents=len(documents),
        observations=len(observations),
        occurrences=sum(item.occurrence_count for item in observations),
    )
