# Circular Electronics Digital Product Passport

The repository now contains the complete Semantic Observatory MVP roadmap
(Phases 0–11) alongside the original DPP knowledge-graph platform.

The knowledge graph platform: a runnable application stack,
versioned ontology, persisted SHACL validation, idempotent ingestion, and a
versioned Product Passport API with responsive operations, a read-only SPARQL and graph
workbench, semantic-quality dashboards, cited governance reports, and verified recovery tooling.

## Start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Or run `./infrastructure/scripts/bootstrap.ps1`.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| Fuseki dataset | http://localhost:3030/dpp |

## Checks

```powershell
cd backend
python -m pip install -e ".[dev]"
ruff check .
mypy app
pytest

cd ../frontend
npm install
npm run typecheck
npm test
npm run build

cd ..
docker compose config --quiet

backend/.venv/Scripts/python scripts/validate_ontology.py
backend/.venv/Scripts/python -m pytest tests/semantic
backend/.venv/Scripts/python -m pytest tests/synthetic
backend/.venv/Scripts/python scripts/security_scan.py

$env:DPP_RUN_LIVE_TESTS="1"
backend/.venv/Scripts/python -m pytest tests/performance
```

Generate the deterministic 10,000-document Observatory dataset with
`backend/.venv/Scripts/python scripts/generate_synthetic.py`.
Import it through `/api/v1/ingestion/files`, validate stored documents through
`/api/v1/validation/documents`, and read aggregate SHACL telemetry from
`/api/v1/validation/summary`.
Collect raw semantic signals through `/api/v1/signals/documents` and inspect
their totals at `/api/v1/signals/summary`.
Calculate the documented Observatory metrics at `/api/v1/metrics`; each metric
has an explain endpoint and supports organisation, domain, date, and time-bucket filters.
Run deterministic drift detection through `/api/v1/incidents/detect` and inspect
traceable findings through `/api/v1/incidents`.
Generate reviewable evidence through `/api/v1/evidence/generate`, then use the
Semantic Observatory workspace for ecosystem, ontology-adoption, validation,
vocabulary/drift, evidence, and organisation views. Run the ground-truth and
scalability evaluation with `./infrastructure/scripts/evaluate.ps1 -Start`.

## Scope

Semantic Observatory tabs are implemented. An optional
future extension for AI-assisted clustering and external standard-hub adapters.

The original DPP platform remains implemented as documented in
`Digital_Product_Passport_BLUEPRINT.md`.

Use `./infrastructure/scripts/reset-environment.ps1` to stop the stack and delete
its local data after an explicit confirmation.

Run `./infrastructure/scripts/demo.ps1` for the reproducible portfolio flow.
Backup and restore commands are documented in `docs/12_Hardening_and_Operations.md`.
