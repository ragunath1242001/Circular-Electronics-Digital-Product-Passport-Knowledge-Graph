# Product Passport API

Phase 4 stores editable product records in PostgreSQL and immutable passport RDF
versions as Fuseki named graphs.

## Workflow

1. `POST /api/v1/products` with a smartphone record.
2. `POST /api/v1/passports` with `{"product_id": "..."}` to create version 1.
3. Update product data with `PUT /api/v1/products/{product_id}`.
4. Snapshot the update with `PUT /api/v1/passports/{passport_id}`.

Product and passport deletion archives metadata; RDF versions remain available
for traceability. Current and historical versions are listed at
`GET /api/v1/passports/{passport_id}/versions`.

## RDF and QR

```text
GET  /api/v1/products/{product_id}/graph
GET  /api/v1/passports/{passport_id}/export?format=turtle
GET  /api/v1/passports/{passport_id}/export?format=json-ld&version=1
POST /api/v1/passports/{passport_id}/validate
GET  /api/v1/passports/{passport_id}/qr
```

The QR endpoint returns SVG, exposes its target in the `X-Passport-URL` response
header, and resolves to the minimal public page at `/passports/{passport_id}`.
Phase 5 can replace that page with the richer React experience without changing
stored passport data.
