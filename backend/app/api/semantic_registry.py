from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Path, Query

from app.schemas.semantic_registry import (
    MappingDefinition,
    OntologyDefinition,
    OntologyVersion,
    RegistryStatus,
    SemanticProfile,
    TermDefinition,
    TermKind,
)
from app.services.semantic_registry import find_term, get_registry, list_terms, ontology_versions

router = APIRouter(prefix="/api/v1", tags=["semantic-registry"])


@router.get("/ontologies", response_model=list[OntologyDefinition])
def ontologies() -> list[OntologyDefinition]:
    return list(get_registry().ontologies)


@router.get("/ontologies/{ontology_id}/versions", response_model=list[OntologyVersion])
def versions(ontology_id: str = Path(min_length=1, max_length=80)) -> list[OntologyVersion]:
    result = ontology_versions(ontology_id)
    if not result:
        raise HTTPException(status_code=404, detail="Ontology not found.")
    return result


@router.get("/profiles", response_model=list[SemanticProfile])
def profiles() -> list[SemanticProfile]:
    return list(get_registry().profiles)


@router.get("/terms", response_model=list[TermDefinition])
def terms(
    ontology_id: str | None = Query(default=None, min_length=1, max_length=80),
    status: RegistryStatus | None = None,
    kind: TermKind | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[TermDefinition]:
    return list_terms(ontology_id, status, kind)[offset : offset + limit]


@router.get("/terms/{term_iri:path}", response_model=TermDefinition)
def term(term_iri: str = Path(min_length=1, max_length=500)) -> TermDefinition:
    result = find_term(unquote(term_iri))
    if result is None:
        raise HTTPException(status_code=404, detail="Term not found.")
    return result


@router.get("/mappings", response_model=list[MappingDefinition])
def mappings(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MappingDefinition]:
    return list(get_registry().mappings[offset : offset + limit])
