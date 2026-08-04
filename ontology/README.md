# Digital Product Passport ontology

Version 1.0.0 defines the Phase 1 vocabulary for circular smartphones and
embedded batteries under `https://example.org/dpp/`.

| Module | Responsibility |
| --- | --- |
| `dpp-core.ttl` | Products, passports, lifecycle, carbon, repair, and recycling |
| `dpp-products.ttl` | Smartphones, batteries, and electronic components |
| `dpp-organizations.ttl` | Economic operators and facilities aligned with W3C ORG |
| `dpp-materials.ttl` | Material occurrences and controlled material types |
| `dpp-provenance.ttl` | Provenance records aligned with PROV-O |
| `dpp-units.ttl` | Quantity values aligned with QUDT |
| `dpp-certificates.ttl` | Certificate identity, issuer, validity, coverage, and evidence |

The executable example is in `examples/circular-phone.ttl`. Validate every
module and competency query from the repository root:

```powershell
backend/.venv/Scripts/python scripts/validate_ontology.py
```

SHACL constraints are in `shapes/`; see `docs/05_SHACL_Validation.md` for the
rules, severity policy, and validation API.
