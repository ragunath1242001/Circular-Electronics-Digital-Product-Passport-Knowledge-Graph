# Data ingestion

The product importer accepts UTF-8 CSV and JSON files up to 2 MB. The Semantic
Observatory importer accepts JSONL batches up to 25 MB through the same endpoint:

```text
POST /api/v1/ingestion/files
GET  /api/v1/ingestion/jobs
GET  /api/v1/ingestion/jobs/{job_id}
GET  /api/v1/ingestion/jobs/{job_id}/errors
```

Uploads are processed synchronously through schema validation, deterministic URI
generation, RDF mapping, SHACL validation, Fuseki named-graph persistence, and
PostgreSQL job accounting. Invalid records are isolated in `ingestion_errors` and
do not prevent valid sibling records from loading.

Each JSONL line must contain the synthetic envelope and embedded JSON-LD payload.
The importer verifies the payload SHA-256 hash, rejects remote JSON-LD contexts,
parses RDF, stores metadata in `dpp_documents`, and persists batches of named graphs
as `urn:dpp:{document-id}`. Semantic faults remain stored for later telemetry;
malformed records are quarantined. Ground-truth files must never be uploaded.

Re-uploading the same source record for the same source system is skipped using a
SHA-256 hash that includes mapping version `1.0.0`. Valid product graphs are stored
as `urn:dpp:graph:passport:{product-id}`.

Example:

```powershell
curl.exe -F "source_system=portfolio-seed" `
  -F "file=@data/seed/smartphones.csv;type=text/csv" `
  http://localhost:8000/api/v1/ingestion/files
```

Synthetic ecosystem import:

```powershell
curl.exe -F "source_system=observatory-synthetic" `
  -F "file=@data/synthetic/generated/documents.jsonl;type=application/x-ndjson" `
  http://localhost:8000/api/v1/ingestion/files
```
