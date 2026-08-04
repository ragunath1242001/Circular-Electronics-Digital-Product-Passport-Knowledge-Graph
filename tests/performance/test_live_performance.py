import csv
import os
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("DPP_RUN_LIVE_TESTS") != "1",
    reason="Set DPP_RUN_LIVE_TESTS=1 for live-stack performance checks.",
)
ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.getenv("DPP_BASE_URL", "http://localhost:8000")


def _timed(client: httpx.Client, method: str, path: str, **kwargs: Any) -> tuple[httpx.Response, float]:
    started = perf_counter()
    response = client.request(method, path, **kwargs)
    elapsed = perf_counter() - started
    response.raise_for_status()
    return response, elapsed


def _ensure_passport(client: httpx.Client) -> tuple[str, str]:
    seed = httpx.Response(200, content=(ROOT / "data/seed/smartphones.json").read_bytes()).json()[0]
    created = client.post("/api/v1/products", json=seed)
    if created.status_code not in {201, 409}:
        created.raise_for_status()
    products = client.get("/api/v1/products?limit=200").raise_for_status().json()
    product = next(item for item in products if item["product_identifier"] == seed["product_identifier"])
    passport = client.get(f"/api/v1/products/{product['id']}/passport")
    if passport.status_code == 404:
        passport = client.post("/api/v1/passports", json={"product_id": product["id"]})
    passport.raise_for_status()
    return product["id"], passport.json()["id"]


def test_live_mvp_performance_targets() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=180) as client:
        product_id, passport_id = _ensure_passport(client)

        _, passport_page = _timed(client, "GET", f"/passports/{passport_id}")
        _, dashboard = _timed(client, "GET", "/api/v1/observability/metrics")
        _, graph = _timed(client, "GET", f"/api/v1/sparql/graph?product_id={product_id}")
        _, validation = _timed(client, "POST", f"/api/v1/passports/{passport_id}/validate")
        templates = client.get("/api/v1/sparql/templates").raise_for_status().json()
        _, sparql = _timed(
            client, "POST", "/api/v1/sparql/query",
            json={"query": templates[0]["query"], "limit": 200},
        )
        report, report_generation = _timed(
            client, "POST", "/api/v1/reports", json={"report_type": "sustainability"},
        )
        _, report_download = _timed(client, "GET", f"/api/v1/reports/{report.json()['id']}/download")

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(
                lambda _: client.get("/api/v1/products?limit=200"), range(16)
            ))
        concurrent_search = perf_counter() - started
        assert all(response.status_code == 200 for response in responses)

        seed_lines = (ROOT / "data/seed/smartphones.csv").read_text(encoding="utf-8").splitlines()
        reader = csv.DictReader(seed_lines)
        first_valid = next(reader)
        assert reader.fieldnames is not None
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
        writer.writeheader()
        # ponytail: duplicate-heavy load; use 1,000 unique passports when tuning ingestion.
        writer.writerows(first_valid for _ in range(1000))
        ingestion, ingestion_time = _timed(
            client, "POST", "/api/v1/ingestion/files",
            data={"source_system": "phase9-performance"},
            files={"file": ("performance.csv", output.getvalue(), "text/csv")},
        )

    assert passport_page < 2
    assert dashboard < 2
    assert graph < 2
    assert validation < 2
    assert sparql < 5
    assert report_generation < 5 and report_download < 2
    assert concurrent_search < 2
    assert ingestion.json()["total_records"] == 1000 and ingestion_time < 180
