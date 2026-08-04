# Reports and Governance

Phase 8 adds cited CSV reports and a report-generation audit trail at `#reports`.

## Reports

| Type | Source data |
| --- | --- |
| Compliance | Passport registry and persisted SHACL validation runs |
| Sustainability | Active product carbon, repairability, and recycled-content fields |
| Supplier quality | Active product supplier and material-completeness fields |
| Certificate | Certificate statements in versioned Fuseki named graphs |

Every report stores its summary, row count, generation time, and source references.
Each exported CSV includes a `source` column. Cells beginning with spreadsheet formula
characters are neutralized before download.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/reports` | Generate and persist one of the four report types |
| `GET /api/v1/reports` | List report history |
| `GET /api/v1/reports/{report_id}` | Read report metadata and citations |
| `GET /api/v1/reports/{report_id}/download` | Download the cited CSV export |
| `GET /api/v1/audit-logs` | List governance events newest first |

Generation is synchronous for the MVP data volume. Each successful report creates a
`REPORT_GENERATED` event without storing credentials, tokens, or source-file contents.
