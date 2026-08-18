CREATE TABLE IF NOT EXISTS semantic_observations (
    id BIGSERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES dpp_documents(document_id),
    observation_type TEXT NOT NULL CHECK (observation_type IN (
        'ontology_version', 'class_usage', 'property_usage', 'namespace_usage',
        'term_classification', 'mapping_used', 'mapping_missing'
    )),
    term_iri TEXT,
    namespace TEXT,
    category TEXT CHECK (category IS NULL OR category IN (
        'standard', 'external_approved', 'custom', 'unknown', 'deprecated'
    )),
    ontology_version TEXT,
    occurrence_count INTEGER NOT NULL CHECK (occurrence_count > 0),
    observed_at TIMESTAMPTZ NOT NULL,
    observation_hash CHAR(64) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS semantic_observations_document_idx
    ON semantic_observations (document_id);
CREATE INDEX IF NOT EXISTS semantic_observations_signal_idx
    ON semantic_observations (observation_type, category, term_iri);
