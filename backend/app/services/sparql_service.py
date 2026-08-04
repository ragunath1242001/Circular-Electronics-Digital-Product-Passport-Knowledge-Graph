import hashlib
import re
from pathlib import Path

from rdflib.plugins.sparql.parser import parseQuery

from app.schemas.sparql import GraphEdge, GraphNode, GraphResult, SparqlQueryResult, SparqlTemplate
from app.services.graph_store import select, select_result

RESOURCE_BASE = "https://example.org/dpp/resource/"
RESOURCE_URI = re.compile(r"https://example\.org/dpp/resource/[a-z0-9/-]+")
READ_QUERY = re.compile(
    r"^\s*(?:(?:PREFIX\s+[\w-]*:\s*<[^>]+>|BASE\s*<[^>]+>)\s*)*SELECT\b",
    re.IGNORECASE | re.DOTALL,
)
TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "sparql" / "competency"


class ReadOnlyQueryError(ValueError):
    pass


def _local_name(uri: str) -> str:
    return re.split(r"[/#]", uri.rstrip("/#"))[-1].replace("-", " ")


def _validate_select(query: str) -> None:
    without_comments = re.sub(r"(?m)^\s*#.*$", "", query)
    if not READ_QUERY.match(without_comments):
        raise ReadOnlyQueryError("Only read-only SELECT queries are allowed.")
    try:
        parseQuery(query)
    except Exception as exc:
        raise ReadOnlyQueryError("The SPARQL query is invalid.") from exc


def list_templates() -> list[SparqlTemplate]:
    templates = []
    for path in sorted(TEMPLATE_DIR.glob("*.rq")):
        identifier = path.stem.split("-", 1)[0]
        title = path.stem.split("-", 1)[1].replace("-", " ").title()
        templates.append(SparqlTemplate(id=identifier, title=title, query=path.read_text()))
    return templates


def run_query(query: str, limit: int) -> SparqlQueryResult:
    _validate_select(query)
    variables, rows = select_result(query)
    return SparqlQueryResult(
        variables=variables,
        rows=rows[:limit],
        truncated=len(rows) > limit,
    )


def explore(root_uri: str) -> GraphResult:
    if not RESOURCE_URI.fullmatch(root_uri):
        raise ValueError("The graph root must be a DPP resource URI.")
    query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX dpp: <https://example.org/dpp/>
SELECT DISTINCT ?source ?predicate ?target ?sourceType ?targetType ?sourceLabel ?targetLabel
WHERE {{
  GRAPH ?graph {{
    {{ BIND(<{root_uri}> AS ?source) ?source ?predicate ?target . FILTER(isIRI(?target)) }}
    UNION
    {{ ?source ?predicate <{root_uri}> . FILTER(isIRI(?source)) BIND(<{root_uri}> AS ?target) }}
    OPTIONAL {{ ?source a ?sourceType }}
    OPTIONAL {{ ?target a ?targetType }}
    OPTIONAL {{ ?source (dct:title|dpp:productIdentifier) ?sourceLabel }}
    OPTIONAL {{ ?target (dct:title|dpp:productIdentifier) ?targetLabel }}
    FILTER(?predicate != rdf:type)
  }}
}}
LIMIT 100"""
    rows = select(query)
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    for row in rows:
        source, target, predicate = row["source"], row["target"], row["predicate"]
        nodes[source] = GraphNode(
            id=source,
            label=row.get("sourceLabel", _local_name(source)),
            type=_local_name(row.get("sourceType", "Resource")),
        )
        nodes[target] = GraphNode(
            id=target,
            label=row.get("targetLabel", _local_name(target)),
            type=_local_name(row.get("targetType", "Resource")),
        )
        edge_id = hashlib.sha1(f"{source}|{predicate}|{target}".encode()).hexdigest()
        edges[edge_id] = GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            label=_local_name(predicate),
        )
    return GraphResult(nodes=list(nodes.values()), edges=list(edges.values()))
