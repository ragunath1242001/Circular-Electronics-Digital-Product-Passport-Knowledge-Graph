from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from rdflib import DCTERMS, OWL, RDF, RDFS, Graph, URIRef
from rdflib import Literal as RdfLiteral
from rdflib.namespace import SKOS

from app.schemas.semantic_registry import (
    MappingDefinition,
    OntologyDefinition,
    OntologyVersion,
    RegistryStatus,
    SemanticProfile,
    TermDefinition,
    TermKind,
)

ONTOLOGY_ROOT = Path(__file__).resolve().parents[3] / "ontology"
REGISTRY_PATH = ONTOLOGY_ROOT / "registry.json"


class _VersionSource(BaseModel):
    path: str
    status: RegistryStatus


class _OntologySource(BaseModel):
    id: str
    namespaces: list[str]
    versions: list[_VersionSource]


class _RegistrySource(BaseModel):
    ontologies: list[_OntologySource]
    profiles: list[SemanticProfile]
    mappings: list[MappingDefinition]


@dataclass(frozen=True)
class SemanticRegistry:
    ontologies: tuple[OntologyDefinition, ...]
    versions: tuple[OntologyVersion, ...]
    profiles: tuple[SemanticProfile, ...]
    terms: tuple[TermDefinition, ...]
    mappings: tuple[MappingDefinition, ...]


def _registry_file(relative_path: str) -> Path:
    path = (ONTOLOGY_ROOT / relative_path).resolve()
    if not path.is_relative_to(ONTOLOGY_ROOT.resolve()) or not path.is_file():
        raise RuntimeError(f"Registry file does not exist: {relative_path}")
    return path


def _required_text(graph: Graph, subject: URIRef, predicate: URIRef, source: str) -> str:
    value = graph.value(subject, predicate)
    if value is None:
        raise RuntimeError(f"{source} is missing {predicate}.")
    return str(value)


def _term_kind(graph: Graph, term: URIRef) -> TermKind:
    types = set(graph.objects(term, RDF.type))
    if OWL.Class in types:
        return "class"
    if OWL.ObjectProperty in types:
        return "object_property"
    if OWL.DatatypeProperty in types:
        return "datatype_property"
    if OWL.AnnotationProperty in types:
        return "annotation_property"
    if SKOS.Concept in types:
        return "concept"
    return "individual"


def _is_deprecated(graph: Graph, term: URIRef) -> bool:
    value = graph.value(term, OWL.deprecated)
    return isinstance(value, RdfLiteral) and value.toPython() is True


@lru_cache
def get_registry() -> SemanticRegistry:
    source = _RegistrySource.model_validate_json(REGISTRY_PATH.read_text(encoding="utf-8"))
    ontologies: list[OntologyDefinition] = []
    versions: list[OntologyVersion] = []
    terms: list[TermDefinition] = []

    for ontology_source in source.ontologies:
        current_versions = [item for item in ontology_source.versions if item.status == "current"]
        if len(current_versions) != 1:
            raise RuntimeError(
                f"Ontology {ontology_source.id} must have exactly one current version."
            )

        ontology_iri = ""
        ontology_title = ""
        current_version = ""
        for version_source in ontology_source.versions:
            path = _registry_file(version_source.path)
            graph = Graph().parse(path, format="turtle")
            ontology_nodes = list(graph.subjects(RDF.type, OWL.Ontology))
            if len(ontology_nodes) != 1 or not isinstance(ontology_nodes[0], URIRef):
                raise RuntimeError(f"{version_source.path} must declare exactly one ontology IRI.")

            node = ontology_nodes[0]
            iri = str(node)
            title = _required_text(graph, node, DCTERMS.title, version_source.path)
            version = _required_text(graph, node, OWL.versionInfo, version_source.path)
            version_iri = _required_text(graph, node, OWL.versionIRI, version_source.path)
            version_terms = sorted(
                {
                    term
                    for term in graph.subjects(RDFS.label)
                    if isinstance(term, URIRef)
                    and any(
                        str(term).startswith(namespace)
                        for namespace in ontology_source.namespaces
                    )
                },
                key=str,
            )
            versions.append(
                OntologyVersion(
                    ontology_id=ontology_source.id,
                    ontology_iri=iri,
                    version=version,
                    version_iri=version_iri,
                    status=version_source.status,
                    source_path=version_source.path,
                    term_count=len(version_terms),
                )
            )
            if version_source.status == "current":
                ontology_iri, ontology_title, current_version = iri, title, version
                terms.extend(
                    TermDefinition(
                        iri=str(term),
                        label=str(graph.value(term, RDFS.label)),
                        kind=_term_kind(graph, term),
                        status="deprecated" if _is_deprecated(graph, term) else "current",
                        ontology_id=ontology_source.id,
                        ontology_version=version,
                    )
                    for term in version_terms
                )

        ontologies.append(
            OntologyDefinition(
                id=ontology_source.id,
                iri=ontology_iri,
                title=ontology_title,
                namespaces=ontology_source.namespaces,
                current_version=current_version,
            )
        )

    known_versions = {(item.ontology_id, item.version) for item in versions}
    for profile in source.profiles:
        for ontology_id, version in profile.ontology_versions.items():
            if (ontology_id, version) not in known_versions:
                raise RuntimeError(
                    f"Profile {profile.id} references unknown {ontology_id} {version}."
                )
        for shape_path in profile.shape_paths:
            _registry_file(shape_path)

    current_term_iris = {item.iri for item in terms}
    for mapping in source.mappings:
        if (mapping.mapping_set, mapping.mapping_version) not in known_versions:
            raise RuntimeError(f"Mapping {mapping.mapping_id} references an unknown version.")
        if {mapping.source_iri, mapping.target_iri} - current_term_iris:
            raise RuntimeError(f"Mapping {mapping.mapping_id} references an unknown term.")

    return SemanticRegistry(
        ontologies=tuple(sorted(ontologies, key=lambda item: item.id)),
        versions=tuple(sorted(versions, key=lambda item: (item.ontology_id, item.version))),
        profiles=tuple(sorted(source.profiles, key=lambda item: item.id)),
        terms=tuple(sorted(terms, key=lambda item: item.iri)),
        mappings=tuple(sorted(source.mappings, key=lambda item: item.mapping_id)),
    )


def ontology_versions(ontology_id: str) -> list[OntologyVersion]:
    return [item for item in get_registry().versions if item.ontology_id == ontology_id]


def find_term(iri: str) -> TermDefinition | None:
    return next((item for item in get_registry().terms if item.iri == iri), None)


def list_terms(
    ontology_id: str | None = None,
    status: RegistryStatus | None = None,
    kind: TermKind | None = None,
) -> list[TermDefinition]:
    return [
        item
        for item in get_registry().terms
        if (ontology_id is None or item.ontology_id == ontology_id)
        and (status is None or item.status == status)
        and (kind is None or item.kind == kind)
    ]
