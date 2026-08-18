from urllib.parse import quote

from fastapi.testclient import TestClient

from app.main import app


def test_semantic_registry_resolves_versions_profiles_and_terms() -> None:
    client = TestClient(app)

    ontologies = client.get("/api/v1/ontologies")
    versions = client.get("/api/v1/ontologies/products/versions")
    profiles = client.get("/api/v1/profiles")
    terms = client.get("/api/v1/terms", params={"ontology_id": "core", "kind": "class"})
    term = client.get(f"/api/v1/terms/{quote('https://example.org/dpp/chemistry', safe='')}")
    mappings = client.get("/api/v1/mappings")

    assert ontologies.status_code == versions.status_code == profiles.status_code == 200
    assert terms.status_code == term.status_code == mappings.status_code == 200
    assert {item["id"] for item in ontologies.json()} >= {"core", "products", "materials"}
    assert [(item["version"], item["status"]) for item in versions.json()] == [
        ("1.0.0", "deprecated"),
        ("1.1.0", "deprecated"),
        ("2.0.0", "current"),
    ]
    assert all(item["ontology_versions"]["products"] == "2.0.0" for item in profiles.json())
    assert any(item["iri"] == "https://example.org/dpp/Product" for item in terms.json())
    assert term.json()["status"] == "deprecated"
    assert mappings.json()[0]["target_iri"] == "https://example.org/dpp/batteryChemistry"
