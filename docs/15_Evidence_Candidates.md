# Evidence candidates and human review

Phase 8 converts recurring Phase 7 incidents and SHACL validation failures into
durable, reviewable evidence candidates. Generation is deterministic and does not
change mappings, profiles, SHACL rules, or ontology versions.

The seven candidate types are `EMERGING_CONCEPT`, `MAPPING_NEEDED`,
`DOCUMENTATION_FRICTION`, `DEPRECATION_MIGRATION_PROBLEM`,
`SHACL_RULE_FRICTION`, `CROSS_SECTOR_MODEL_CONFLICT`, and
`VERSION_MIGRATION_FRICTION`.

Each candidate records affected concepts, first and last observation times,
occurrence/organisation/domain counts, trend and persistence, mapping status,
conformance impact, transparent source metrics, a human-review recommendation,
and up to 100 provenance references. Literal passport payloads are not retained.

```text
POST  /api/v1/evidence/generate
GET   /api/v1/evidence
GET   /api/v1/evidence?candidate_type=MAPPING_NEEDED&status=NEW
GET   /api/v1/evidence/{candidate_id}
PATCH /api/v1/evidence/{candidate_id}
```

Reviewers can set `NEW`, `MARKED_FOR_REVIEW`, or `DISMISSED` and attach an
annotation. Regeneration updates measurements while preserving that human status
and annotation. The API's JSON response is the Phase 8 export format.
