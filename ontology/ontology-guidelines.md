# Ontology guidelines

- Use `https://example.org/dpp/` for vocabulary terms and
  `https://example.org/dpp/resource/` for example resources.
- Mint deterministic, readable IRIs; never use database identifiers or blank
  nodes for products, organizations, facilities, materials, evidence, or provenance.
- Version every ontology module with `owl:versionIRI` and `owl:versionInfo`.
- Reuse Dublin Core Terms, PROV-O, W3C ORG, SKOS, and QUDT before adding local terms.
- Keep OWL descriptive. Put required fields, ranges, and cross-field validation in SHACL.
- Treat a material occurrence as `dpp:Material` and connect it to a controlled
  `dpp:MaterialType`; this preserves supplier, origin, and percentage per occurrence.

