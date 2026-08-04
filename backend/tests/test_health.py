from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Digital Product Passport",
        "environment": None,
    }
    assert response.headers["x-request-id"]


def test_ready() -> None:
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_metrics_include_request_counts() -> None:
    client = TestClient(app)
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "dpp_http_requests_total" in response.text
    assert 'route="/health"' in response.text
