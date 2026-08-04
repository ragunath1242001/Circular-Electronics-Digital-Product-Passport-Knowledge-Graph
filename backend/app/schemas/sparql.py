from pydantic import BaseModel, Field


class SparqlTemplate(BaseModel):
    id: str
    title: str
    query: str


class SparqlQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=200, ge=1, le=500)


class SparqlQueryResult(BaseModel):
    variables: list[str]
    rows: list[dict[str, str]]
    truncated: bool


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str


class GraphResult(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
