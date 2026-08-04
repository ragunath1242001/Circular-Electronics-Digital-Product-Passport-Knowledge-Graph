CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id UUID PRIMARY KEY,
    source_system TEXT NOT NULL,
    file_name TEXT NOT NULL,
    data_format TEXT NOT NULL CHECK (data_format IN ('csv', 'json')),
    mapping_version TEXT NOT NULL,
    status TEXT NOT NULL,
    total_records INTEGER NOT NULL DEFAULT 0,
    imported_records INTEGER NOT NULL DEFAULT 0,
    duplicate_records INTEGER NOT NULL DEFAULT 0,
    quarantined_records INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_errors (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES ingestion_jobs(id) ON DELETE CASCADE,
    record_number INTEGER NOT NULL,
    product_identifier TEXT,
    error_code TEXT NOT NULL,
    message TEXT NOT NULL,
    raw_record JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingested_records (
    source_system TEXT NOT NULL,
    product_identifier TEXT NOT NULL,
    record_hash CHAR(64) NOT NULL,
    mapping_version TEXT NOT NULL,
    graph_uri TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (source_system, record_hash)
);

CREATE INDEX IF NOT EXISTS ingestion_jobs_created_at_idx ON ingestion_jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS ingestion_errors_job_id_idx ON ingestion_errors (job_id);

