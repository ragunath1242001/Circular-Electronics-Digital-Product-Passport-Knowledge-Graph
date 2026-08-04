# Hardening and Operations

Phase 9 adds executable security, performance, recovery, monitoring, and demo checks.

## Security

The API enforces bounded inputs, file type and size checks, read-only SPARQL, exact
CORS origins, stable resource URIs, CSV formula neutralization, request IDs, and
defensive response headers. The frontend adds frame, content-type, referrer, and
browser-permission headers.

Run the source and dependency scans:

```powershell
backend/.venv/Scripts/python scripts/security_scan.py
backend/.venv/Scripts/python -m pip_audit backend --strict
cd frontend
npm audit --audit-level=critical
```

The local demo login is not production authentication. JWT expiry, role restrictions,
and unauthorized private-route tests remain outside this single-user MVP; add an
identity provider and backend authorization before exposing write endpoints to multiple
users or the public internet.

## Monitoring

- `/health` is the liveness endpoint.
- `/ready` identifies the environment and readiness state.
- `/metrics` exposes process uptime, request totals, and aggregate request duration in
  Prometheus text format.
- Application logs are structured JSON and carry request IDs, status, route, and timing.

Docker health checks cover PostgreSQL, Redis, Fuseki, and the backend. The frontend
depends on a healthy backend.

## Backup and restore

Backups contain a clean PostgreSQL dump, a stopped-and-consistent Fuseki volume archive,
and SHA-256 checksums. Redis is excluded because it holds no authoritative business data.

```powershell
./infrastructure/scripts/backup.ps1 -OutputDirectory ./backups/manual
./infrastructure/scripts/restore.ps1 -BackupDirectory ./backups/manual
```

Restore verifies checksums and requires typing `RESTORE`; automation may pass `-Force`.
It replaces the application PostgreSQL schema and the resolved Fuseki Docker volume,
then waits for the complete stack to become healthy.

## Performance and portfolio demo

With the stack running:

```powershell
./infrastructure/scripts/demo.ps1

$env:DPP_RUN_LIVE_TESTS="1"
backend/.venv/Scripts/python -m pytest tests/performance -q
```

The live suite checks concurrent product reads, dashboard metrics, passport rendering,
SHACL validation, SPARQL, graph expansion, report generation/download, and a 1,000-row
ingestion within the MVP thresholds. The demo idempotently creates its product and
passport, validates it, queries and explores the graph, calculates semantic quality,
and downloads a cited sustainability report to `artifacts/`.
