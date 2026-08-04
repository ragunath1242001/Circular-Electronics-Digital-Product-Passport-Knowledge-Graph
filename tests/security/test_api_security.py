from app.main import app
from fastapi.testclient import TestClient

from scripts.security_scan import ROOT, scan


def test_public_api_security_boundaries() -> None:
    client = TestClient(app)

    update = client.post(
        "/api/v1/sparql/query",
        json={"query": "DELETE WHERE { ?s ?p ?o }", "limit": 10},
    )
    oversized = client.post(
        "/api/v1/sparql/query",
        json={"query": "SELECT * WHERE { ?s ?p ?o }" + " " * 20_001, "limit": 10},
    )
    traversal = client.post(
        "/api/v1/ingestion/files",
        data={"source_system": "security-test"},
        files={"file": ("../../payload.exe", b"malicious", "application/octet-stream")},
    )
    allowed_cors = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied_cors = client.options(
        "/health",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    health = client.get("/health")

    assert update.status_code == 422
    assert oversized.status_code == 422
    assert traversal.status_code == 415
    assert allowed_cors.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert denied_cors.status_code == 400
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert scan(ROOT) == []
