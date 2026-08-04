from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db.passports import get_product
from app.schemas.sparql import GraphResult, SparqlQueryRequest, SparqlQueryResult, SparqlTemplate
from app.semantic.uri_factory import resource_uri
from app.services.graph_store import GraphStoreError
from app.services.sparql_service import ReadOnlyQueryError, explore, list_templates, run_query

router = APIRouter(prefix="/api/v1/sparql", tags=["sparql"])


@router.get("/templates", response_model=list[SparqlTemplate])
def templates() -> list[SparqlTemplate]:
    return list_templates()


@router.post("/query", response_model=SparqlQueryResult)
def query(request: SparqlQueryRequest) -> SparqlQueryResult:
    try:
        return run_query(request.query, request.limit)
    except ReadOnlyQueryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/graph", response_model=GraphResult)
def graph(
    product_id: UUID | None = None,
    root_uri: str | None = Query(default=None, max_length=500),
) -> GraphResult:
    if (product_id is None) == (root_uri is None):
        raise HTTPException(status_code=422, detail="Provide exactly one product_id or root_uri.")
    if product_id is not None:
        product = get_product(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found.")
        root_uri = str(resource_uri("product", product.product_identifier))
    try:
        return explore(root_uri or "")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GraphStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
