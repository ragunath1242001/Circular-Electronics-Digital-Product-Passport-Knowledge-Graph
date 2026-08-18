CREATE TABLE IF NOT EXISTS semantic_validation_runs (
    id UUID PRIMARY KEY,
    document_id TEXT NOT NULL UNIQUE REFERENCES dpp_documents(document_id),
    organisation_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    semantic_profile_id TEXT NOT NULL,
    declared_ontology_version TEXT NOT NULL,
    conforms BOOLEAN NOT NULL,
    violations INTEGER NOT NULL,
    warnings INTEGER NOT NULL,
    info INTEGER NOT NULL,
    validated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_observations (
    id BIGSERIAL PRIMARY KEY,
    validation_run_id UUID NOT NULL REFERENCES semantic_validation_runs(id) ON DELETE CASCADE,
    focus_node_hash CHAR(64) NOT NULL,
    result_path TEXT,
    constraint_component TEXT,
    source_shape TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('Violation', 'Warning', 'Info')),
    message_code CHAR(16) NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS semantic_validation_runs_dimensions_idx
    ON semantic_validation_runs (domain, semantic_profile_id, declared_ontology_version);
CREATE INDEX IF NOT EXISTS validation_observations_diagnostics_idx
    ON validation_observations (severity, result_path, constraint_component);
