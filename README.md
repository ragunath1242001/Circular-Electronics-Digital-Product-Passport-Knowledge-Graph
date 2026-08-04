# Circular Electronics Digital Product Passport

Phases 0–9 of the knowledge graph platform: a runnable application stack,
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
backend/.venv/Scripts/python scripts/security_scan.py

$env:DPP_RUN_LIVE_TESTS="1"
backend/.venv/Scripts/python -m pytest tests/performance
```

## Scope

This repository implements Phases 0–9 from
[the implementation blueprint](Digital_Product_Passport_BLUEPRINT.md).

Use `./infrastructure/scripts/reset-environment.ps1` to stop the stack and delete
its local data after an explicit confirmation.

Run `./infrastructure/scripts/demo.ps1` for the reproducible portfolio flow.
Backup and restore commands are documented in `docs/12_Hardening_and_Operations.md`.
