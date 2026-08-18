# Dashboard API, observatory UI, and evaluation

Phases 9 and 10 add dashboard-oriented read endpoints and six linked semantic
observatory views. The UI renders canonical backend values and links every metric
to its `/api/v1/metrics/{metric_id}/explain` response.

Additional read endpoints:

```text
GET /api/v1/ecosystem/summary
GET /api/v1/ecosystem/organisations/{organisation_id}
GET /api/v1/terms/unknown
GET /api/v1/terms/deprecated
GET /api/v1/terms/custom
GET /api/v1/validation/constraints
GET /api/v1/validation/constraints/{constraint_id}
GET /api/v1/ontologies/products/adoption
GET /api/v1/mappings/gaps
```

The UI provides overview, ontology adoption, validation intelligence,
vocabulary/drift, evidence review, and organisation detail views under the
`Semantic observatory` workspace entry.

Phase 11 is reproducible from the repository root while the stack is running:

```powershell
./infrastructure/scripts/evaluate.ps1 -Start
```

It writes JSON and Markdown reports to `artifacts/`, evaluates unknown,
deprecated, mapping-gap, version, and configured-fragmentation detection against
seeded ground truth, checks metric formulas and provenance, benchmarks 1k/10k/25k
generation/JSONL parsing, and measures common dashboard API latency. Validation
throughput at 25k and semantic coherence are explicitly left unclaimed rather
than inferred.
