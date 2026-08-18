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

## Observatory telemetry

Stored JSONL documents are validated against the shape files declared by their
semantic profile. Validation is resumable: documents with an existing telemetry
run are skipped.

```text
POST /api/v1/validation/documents?limit=100
GET  /api/v1/validation/summary
```

Each document run records its organisation, domain, profile, declared ontology
version, timestamp, and severity totals. Diagnostic observations retain the result
path, constraint component, source shape, severity, message, and a stable message
code. Focus nodes are SHA-256 hashed and RDF values are not copied into PostgreSQL.
