# Semantic observability

Phase 7 exposes reproducible quality metrics at:

```text
GET /api/v1/observability/metrics
GET /api/v1/observability/metrics?manufacturer=Eco%20Devices%20BV
GET /api/v1/observability/metrics?supplier=Circular%20Cells%20GmbH&model=CFX2-EU
```

The service reads the latest passport version per product from Fuseki and reads
persisted validation reports from PostgreSQL. Product filters apply to graph
coverage, vocabulary, ontology-version, and supplier metrics; validation trends
and SHACL conformance summarize the shared validation history.

The semantic quality score is returned with every input component and weight:

```text
30% completeness
25% SHACL conformance
20% provenance coverage
15% controlled vocabulary conformance
10% reference integrity
```

Weights are configurable through the five `QUALITY_WEIGHT_*` environment values.
The service divides the weighted component sum by the configured total weight,
so the score remains reproducible even when weights are customized.

The dashboard is available under `#observability` and includes filters, score
composition, 30-day validation trends, exceptions, failing rules, vocabulary
usage, ontology-version distribution, and supplier completeness.

Passports minted before Phase 7 appear as `Unrecorded` in the ontology-version
distribution until a new passport version is created.

## Observatory raw signals

The Observatory collector records raw facts for stored JSONL documents without
calculating metrics:

- RDF class, property, and namespace usage;
- declared product-ontology version;
- standard, approved-external, custom, unknown, and deprecated term classes;
- approved mapping use and missing mappings.

Collection is resumable and stores counts, not RDF payload values.

```text
POST /api/v1/signals/documents?limit=100
GET  /api/v1/signals/summary
```
