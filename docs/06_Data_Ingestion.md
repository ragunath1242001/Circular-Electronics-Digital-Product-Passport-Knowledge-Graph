# Data ingestion

Phase 3 accepts UTF-8 CSV and JSON files up to 2 MB at:

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

Re-uploading the same source record for the same source system is skipped using a
SHA-256 hash that includes mapping version `1.0.0`. Valid product graphs are stored
as `urn:dpp:graph:passport:{product-id}`.

Example:

```powershell
curl.exe -F "source_system=portfolio-seed" `
  -F "file=@data/seed/smartphones.csv;type=text/csv" `
  http://localhost:8000/api/v1/ingestion/files
```

