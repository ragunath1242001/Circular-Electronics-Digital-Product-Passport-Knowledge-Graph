DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'ingestion_jobs'::regclass
          AND conname = 'ingestion_jobs_data_format_check'
          AND POSITION('jsonl' IN pg_get_constraintdef(oid)) = 0
    ) THEN
        ALTER TABLE ingestion_jobs DROP CONSTRAINT ingestion_jobs_data_format_check;
        ALTER TABLE ingestion_jobs ADD CONSTRAINT ingestion_jobs_data_format_check
            CHECK (data_format IN ('csv', 'json', 'jsonl'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS dpp_documents (
    id UUID PRIMARY KEY,
    document_id TEXT NOT NULL UNIQUE,
    job_id UUID NOT NULL REFERENCES ingestion_jobs(id),
    source_system TEXT NOT NULL,
    external_identifier TEXT NOT NULL,
    organisation_id TEXT NOT NULL,
    domain TEXT NOT NULL CHECK (domain IN ('electronics', 'battery')),
    semantic_profile_id TEXT NOT NULL,
    declared_ontology_version TEXT NOT NULL,
    document_hash CHAR(64) NOT NULL UNIQUE,
    graph_uri TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'STORED' CHECK (status IN ('STORED')),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS dpp_documents_organisation_idx
    ON dpp_documents (organisation_id);
CREATE INDEX IF NOT EXISTS dpp_documents_domain_version_idx
    ON dpp_documents (domain, declared_ontology_version);
