CREATE TABLE IF NOT EXISTS evidence_candidates (
    id UUID PRIMARY KEY,
    candidate_type TEXT NOT NULL CHECK (candidate_type IN (
        'EMERGING_CONCEPT', 'MAPPING_NEEDED', 'DOCUMENTATION_FRICTION',
        'DEPRECATION_MIGRATION_PROBLEM', 'SHACL_RULE_FRICTION',
        'CROSS_SECTOR_MODEL_CONFLICT', 'VERSION_MIGRATION_FRICTION'
    )),
    status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN (
        'NEW', 'MARKED_FOR_REVIEW', 'DISMISSED'
    )),
    label TEXT NOT NULL,
    affected_concepts JSONB NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    occurrence_count INTEGER NOT NULL CHECK (occurrence_count >= 0),
    organisation_count INTEGER NOT NULL CHECK (organisation_count >= 0),
    domain_count INTEGER NOT NULL CHECK (domain_count >= 0),
    trend TEXT NOT NULL CHECK (trend IN (
        'increasing', 'stable', 'decreasing', 'insufficient_history'
    )),
    growth_rate DOUBLE PRECISION,
    persistence_days INTEGER NOT NULL CHECK (persistence_days >= 1),
    mapping_status TEXT NOT NULL CHECK (mapping_status IN (
        'missing', 'approved', 'not_applicable'
    )),
    conformance_impact INTEGER NOT NULL CHECK (conformance_impact >= 0),
    metrics JSONB NOT NULL,
    recommendation TEXT NOT NULL,
    source_incident_id UUID REFERENCES semantic_incidents(id),
    evidence_references JSONB NOT NULL,
    evidence_version TEXT NOT NULL,
    annotation TEXT,
    candidate_key CHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS evidence_candidates_filter_idx
    ON evidence_candidates (status, candidate_type, occurrence_count DESC);
