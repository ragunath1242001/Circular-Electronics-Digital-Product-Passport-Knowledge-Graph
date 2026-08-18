# Backend

FastAPI bootstrap for the Digital Product Passport platform.

Validation endpoints are available under `/api/v1/validation/runs`; submitted
Turtle or JSON-LD is checked with SHACL and its report is persisted in PostgreSQL.
Stored Observatory documents can be validated in resumable batches at
`/api/v1/validation/documents`, with aggregate telemetry at
`/api/v1/validation/summary`.
Raw vocabulary, version, classification, and mapping signals are collected at
`/api/v1/signals/documents` and summarized at `/api/v1/signals/summary`.
The ten documented Observatory metrics are available from `/api/v1/metrics`,
with formulas and edge cases at `/api/v1/metrics/{metric_id}/explain`.
Versioned deterministic drift detectors run at `/api/v1/incidents/detect`, with
filterable incident list and detail endpoints under `/api/v1/incidents`.
Evidence generation and human review are available under `/api/v1/evidence`.
Dashboard read models cover ecosystem summary, classified terms, constraint
intelligence, ontology adoption, mapping gaps, and organisation detail.
CSV and JSON uploads are available under `/api/v1/ingestion/files`, with job and
quarantine details under `/api/v1/ingestion/jobs`.
The same upload route streams bounded Observatory JSONL batches into PostgreSQL
document metadata and Fuseki named graphs with hash-based idempotency.
Product and passport CRUD is available under `/api/v1/products` and
`/api/v1/passports`, including immutable RDF versions, JSON-LD/Turtle exports,
SHACL validation, and SVG QR codes.
Semantic health metrics are available at `/api/v1/observability/metrics`, with
manufacturer, supplier, and product-model filters.
The read-only SPARQL workbench is available under `/api/v1/sparql`, including
20 saved templates and one-hop DPP resource graph expansion.
The version-controlled semantic registry is available under `/api/v1/ontologies`,
`/api/v1/profiles`, `/api/v1/terms`, and `/api/v1/mappings`.
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
