from fastapi.testclient import TestClient

from app.main import app


def test_ingestion_rejects_unsupported_file_types() -> None:
    response = TestClient(app).post(
        "/api/v1/ingestion/files",
        data={"source_system": "test"},
        files={"file": ("products.txt", b"not supported", "text/plain")},
    )

    assert response.status_code == 415

