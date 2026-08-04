import pytest

from app.services.sparql_service import ReadOnlyQueryError, _validate_select


def test_query_guard_allows_select_and_blocks_updates() -> None:
    _validate_select("PREFIX dpp: <https://example.org/dpp/> SELECT ?s WHERE { ?s ?p ?o }")
    with pytest.raises(ReadOnlyQueryError, match="read-only SELECT"):
        _validate_select("INSERT DATA { <urn:a> <urn:b> <urn:c> }")
