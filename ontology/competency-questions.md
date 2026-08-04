# Competency questions

Each question is backed by an executable SPARQL query tested against
`examples/circular-phone.ttl`.

| # | Question | Query |
| --- | --- | --- |
| 1 | Which smartphones were made by which manufacturers? | `01-smartphones-and-manufacturers.rq` |
| 2 | Which components belong to product CFX1? | `02-product-components.rq` |
| 3 | Which materials and mass percentages occur in batteries? | `03-battery-materials.rq` |
| 4 | Which products have user-replaceable batteries? | `04-user-replaceable-batteries.rq` |
| 5 | Which products have software support below eight years? | `05-software-support-below-threshold.rq` |
| 6 | Which products have expired certificates? | `06-expired-certificates.rq` |
| 7 | Which products exceed the carbon threshold? | `07-high-carbon-footprint.rq` |
| 8 | Which products exceed the repairability threshold? | `08-repairability-above-threshold.rq` |
| 9 | Which products exceed the recycled-content threshold? | `09-recycled-content-above-threshold.rq` |
| 10 | Where do a product's materials originate? | `10-product-to-material-origin.rq` |
| 11 | Which recyclers handle each product? | `11-product-to-recycler.rq` |
| 12 | Which suppliers provide critical materials? | `12-critical-materials-by-supplier.rq` |
| 13 | Which claims lack provenance? | `13-missing-provenance-claims.rq` |
| 14 | Which suppliers are associated with validation failures? | `14-suppliers-with-validation-failures.rq` |
| 15 | Which ontology versions are in use? | `15-ontology-versions-in-use.rq` |
| 16 | Where are deprecated properties used? | `16-deprecated-properties.rq` |
| 17 | Which products lack recycling instructions? | `17-products-missing-recycling-instructions.rq` |
| 18 | How do product models compare? | `18-compare-product-models.rq` |
| 19 | Which passport versions describe which products? | `19-passport-versions.rq` |
| 20 | What path connects products to supply-chain origins? | `20-supply-chain-path.rq` |

Queries live in `sparql/competency/` and deliberately use fixed demo thresholds.
The Phase 6 workbench also accepts custom read-only `SELECT` queries.
