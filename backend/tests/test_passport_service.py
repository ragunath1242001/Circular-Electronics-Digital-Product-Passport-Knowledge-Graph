from uuid import UUID

from rdflib import Graph

from app.schemas.passports import PassportVersion
from app.services import passport_service


def test_passport_export_supports_turtle_and_json_ld(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    passport_id = UUID("00000000-0000-0000-0000-000000000001")
    turtle = b"<https://example.org/product/1> <https://example.org/name> \"Phone\" ."
    stored = PassportVersion(
        passport_id=passport_id,
        version=1,
        graph_uri="urn:dpp:graph:passport:test:v1",
        created_at="2026-08-04T00:00:00Z",
    )
    monkeypatch.setattr(passport_service, "get_passport_version", lambda *_: stored)
    monkeypatch.setattr(passport_service, "get_graph", lambda *_: turtle)

    turtle_export = passport_service.export_passport_graph(passport_id, None, "turtle")
    json_ld_export = passport_service.export_passport_graph(passport_id, 1, "json-ld")

    assert turtle_export == turtle
    assert len(Graph().parse(data=json_ld_export.decode(), format="json-ld")) == 1
