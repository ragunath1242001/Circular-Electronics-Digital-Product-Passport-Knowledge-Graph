from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RegistryStatus = Literal["current", "deprecated"]
TermKind = Literal[
    "class",
    "object_property",
    "datatype_property",
    "annotation_property",
    "concept",
    "individual",
]
MappingRelation = Literal[
    "skos:exactMatch",
    "skos:closeMatch",
    "skos:broadMatch",
    "skos:narrowMatch",
    "owl:equivalentProperty",
    "owl:equivalentClass",
]
MappingStatus = Literal["proposed", "approved", "deprecated"]


class OntologyVersion(BaseModel):
    ontology_id: str
    ontology_iri: str
    version: str
    version_iri: str
    status: RegistryStatus
    source_path: str
    term_count: int = Field(ge=0)


class OntologyDefinition(BaseModel):
    id: str
    iri: str
    title: str
    namespaces: list[str]
    current_version: str


class SemanticProfile(BaseModel):
    id: str
    domain: str
    ontology_versions: dict[str, str]
    shape_paths: list[str]
    accepted_namespaces: list[str]
    status: RegistryStatus


class TermDefinition(BaseModel):
    iri: str
    label: str
    kind: TermKind
    status: RegistryStatus
    ontology_id: str
    ontology_version: str


class MappingDefinition(BaseModel):
    mapping_id: str
    source_iri: str
    target_iri: str
    relation: MappingRelation
    mapping_set: str
    mapping_version: str
    status: MappingStatus
    provenance: str
    created_at: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)
