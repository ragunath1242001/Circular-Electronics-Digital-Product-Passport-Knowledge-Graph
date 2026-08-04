CREATE TABLE IF NOT EXISTS report_jobs (
    id UUID PRIMARY KEY,
    report_type TEXT NOT NULL CHECK (
        report_type IN ('compliance', 'sustainability', 'supplier-quality', 'certificate')
    ),
    status TEXT NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('COMPLETED', 'FAILED')),
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    summary JSONB NOT NULL,
    sources JSONB NOT NULL,
    content JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    result TEXT NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS report_jobs_generated_at_idx ON report_jobs (generated_at DESC);
CREATE INDEX IF NOT EXISTS audit_logs_created_at_idx ON audit_logs (created_at DESC);
