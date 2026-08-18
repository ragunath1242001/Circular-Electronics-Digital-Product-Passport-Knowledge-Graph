# Observatory metrics

Phase 6 calculates versioned metrics directly from stored validation and semantic
observations. No composite interoperability score is produced.

```text
GET /api/v1/metrics
GET /api/v1/metrics?metric_id=MET-002&domain=battery
GET /api/v1/metrics?organisation=org-01&from=2026-08-01&to=2026-08-31
GET /api/v1/metrics?granularity=day
GET /api/v1/metrics/{metric_id}/explain
```

| ID | Metric | Formula |
| --- | --- | --- |
| MET-001 | Current ontology adoption | current documents / resolvable-version documents |
| MET-002 | Vocabulary reuse | standard and approved-external usages / classified usages |
| MET-003 | Custom term ratio | custom usages / classified usages |
| MET-004 | Unknown term ratio | unknown usages / inspected term usages |
| MET-005 | DPP SHACL conformance | zero-violation documents / validated documents |
| MET-006 | Constraint conformance | evaluations without violation / evaluations |
| MET-007 | Version consistency | modal-version documents / versioned documents |
| MET-008 | Mapping coverage | mapped concepts / concepts classified as mappable |
| MET-009 | Semantic fragmentation | 1 - dominant representation usages / group usages |
| MET-010 | Deprecated usage | deprecated usages / registered-model usages |

Every response includes numerator, denominator, component counts, calculation
version, and optional per-constraint, per-version, or per-concept-group breakdowns.
Zero denominators return `null`. Constraint denominators use SHACL targets and
ontology subclass closure. Approved registry mappings define fragmentation groups.
