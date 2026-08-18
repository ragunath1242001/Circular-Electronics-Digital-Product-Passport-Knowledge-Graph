# Semantic drift detection

Phase 7 runs six deterministic, versioned detectors over stored semantic telemetry.
Thresholds live in `data/detectors.json`; changing them does not require application
code changes.

| ID | Detector | Trigger |
| --- | --- | --- |
| DET-001 | Unknown term | Registered minimum occurrence count |
| DET-002 | Deprecated term | Registered minimum occurrence count |
| DET-003 | Version drift | Legacy share threshold or sustained increase |
| DET-004 | Custom vocabulary growth | Share threshold or rolling growth |
| DET-005 | Fragmentation | Configured mapping-group fragmentation threshold |
| DET-006 | Mapping gap | Minimum unmapped-concept occurrences |

```text
POST /api/v1/incidents/detect
GET  /api/v1/incidents
GET  /api/v1/incidents?detector_type=DET-006&severity=critical
GET  /api/v1/incidents/{incident_id}
```

Each incident stores dimensions, severity, affected entities, observed and baseline
values, the rule that fired, bounded observation references, an explanation, and
the detector version. Re-running detection updates the same incident key instead
of creating duplicates. Statistical anomaly detection remains outside the MVP.
