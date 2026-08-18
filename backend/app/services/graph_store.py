import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings


class GraphStoreError(RuntimeError):
    """Raised when Fuseki cannot read or persist a named graph."""


def _url(graph_uri: str) -> str:
    return f"{get_settings().fuseki_url.rstrip('/')}/data?graph={quote(graph_uri, safe='')}"


def put_graph(graph_data: bytes, graph_uri: str) -> None:
    request = Request(
        _url(graph_uri),
        data=graph_data,
        method="PUT",
        headers={"Content-Type": "text/turtle"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status not in {200, 201, 204}:
                raise GraphStoreError(f"Fuseki returned HTTP {response.status}")
    except (HTTPError, URLError) as exc:
        raise GraphStoreError(f"Fuseki graph persistence failed: {exc.reason}") from exc


def post_dataset(graph_data: bytes) -> None:
    request = Request(
        f"{get_settings().fuseki_url.rstrip('/')}/data",
        data=graph_data,
        method="POST",
        headers={"Content-Type": "application/trig"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in {200, 201, 204}:
                raise GraphStoreError(f"Fuseki returned HTTP {response.status}")
    except (HTTPError, URLError) as exc:
        raise GraphStoreError(f"Fuseki dataset persistence failed: {exc.reason}") from exc


def get_graph(graph_uri: str) -> bytes:
    request = Request(_url(graph_uri), headers={"Accept": "text/turtle"})
    try:
        with urlopen(request, timeout=15) as response:
            return bytes(response.read())
    except HTTPError as exc:
        if exc.code == 404:
            raise GraphStoreError("Passport graph was not found in Fuseki.") from exc
        raise GraphStoreError(f"Fuseki graph read failed: {exc.reason}") from exc
    except URLError as exc:
        raise GraphStoreError(f"Fuseki graph read failed: {exc.reason}") from exc


def delete_graph(graph_uri: str) -> None:
    try:
        with urlopen(Request(_url(graph_uri), method="DELETE"), timeout=15):
            pass
    except HTTPError as exc:
        if exc.code != 404:
            raise GraphStoreError(f"Fuseki graph deletion failed: {exc.reason}") from exc
    except URLError as exc:
        raise GraphStoreError(f"Fuseki graph deletion failed: {exc.reason}") from exc


def select_result(query: str) -> tuple[list[str], list[dict[str, str]]]:
    request = Request(
        f"{get_settings().fuseki_url.rstrip('/')}/query",
        data=urlencode({"query": query}).encode(),
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload: dict[str, Any] = json.load(response)
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        reason = getattr(exc, "reason", str(exc))
        raise GraphStoreError(f"Fuseki query failed: {reason}") from exc
    rows = [
        {name: str(value["value"]) for name, value in binding.items()}
        for binding in payload["results"]["bindings"]
    ]
    return [str(name) for name in payload["head"].get("vars", [])], rows


def select(query: str) -> list[dict[str, str]]:
    return select_result(query)[1]
