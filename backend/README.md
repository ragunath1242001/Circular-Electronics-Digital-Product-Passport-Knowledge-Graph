# Backend

FastAPI bootstrap for the Digital Product Passport platform.

Validation endpoints are available under `/api/v1/validation/runs`; submitted
Turtle or JSON-LD is checked with SHACL and its report is persisted in PostgreSQL.
CSV and JSON uploads are available under `/api/v1/ingestion/files`, with job and
quarantine details under `/api/v1/ingestion/jobs`.
Product and passport CRUD is available under `/api/v1/products` and
`/api/v1/passports`, including immutable RDF versions, JSON-LD/Turtle exports,
SHACL validation, and SVG QR codes.
Semantic health metrics are available at `/api/v1/observability/metrics`, with
manufacturer, supplier, and product-model filters.
The read-only SPARQL workbench is available under `/api/v1/sparql`, including
20 saved templates and one-hop DPP resource graph expansion.
Compliance, sustainability, supplier-quality, and certificate reports are
available under `/api/v1/reports`; governance events are listed at
`/api/v1/audit-logs`.
Service health is available at `/health` and `/ready`; Prometheus-compatible
request and uptime metrics are exposed at `/metrics`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Run checks with `ruff check .`, `mypy app`, and `pytest`.
