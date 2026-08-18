# Digital Product Passport ontology

The registry defines the circular-smartphone vocabulary under
`https://example.org/dpp/`. The products module is current at 2.0.0; unchanged
supporting modules remain at 1.0.0.

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

`registry.json` declares the current ontology packages, electronics and battery
SHACL profiles, accepted external namespaces, and semantic mappings exposed by
the backend registry API. RDF remains the source of truth for ontology identity,
versions, labels, term kinds, and deprecation status.

Products 1.0.0 and 1.1.0 are preserved under `history/products/`. Products 2.0.0
replaces deprecated `dpp:chemistry` with `dpp:batteryChemistry`; the approved
equivalence mapping remains queryable for migration and drift analysis.
