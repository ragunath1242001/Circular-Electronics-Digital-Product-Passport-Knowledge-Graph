CREATE TABLE IF NOT EXISTS validation_runs (
    id UUID PRIMARY KEY,
    conforms BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    violations INTEGER NOT NULL,
    warnings INTEGER NOT NULL,
    info INTEGER NOT NULL,
    results JSONB NOT NULL,
    report_turtle TEXT NOT NULL
);

