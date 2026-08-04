# SHACL validation

Phase 2 validates submitted Turtle or JSON-LD with PySHACL, the versioned DPP
ontology, and four shape modules in `ontology/shapes/`.

## Rules

- Product rules enforce identifiers and passport linkage.
- Smartphone rules enforce manufacturer, model granularity, core components,
  lifecycle, repairability, software support, recycling, and carbon data.
- Battery rules enforce identity, chemistry, capacity and unit, durability,
  replaceability, materials, carbon, end-of-life guidance, operator, and provenance.
- Certificate rules enforce identity, issuer, covered entity, evidence, and date order.
- Violations fail conformance. Warnings and informational results remain visible
  without making an otherwise valid graph non-conformant.

## API

```text
POST /api/v1/validation/runs
GET  /api/v1/validation/runs
GET  /api/v1/validation/runs/{run_id}
```

Every API validation run stores its summary, detailed results, and Turtle SHACL
report in PostgreSQL. Request payloads are limited to 2 MB and are never logged.

