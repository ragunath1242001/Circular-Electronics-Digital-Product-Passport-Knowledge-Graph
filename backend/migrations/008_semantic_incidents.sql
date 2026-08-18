CREATE TABLE IF NOT EXISTS semantic_incidents (
    id UUID PRIMARY KEY,
    detector_type TEXT NOT NULL CHECK (detector_type IN (
        'DET-001', 'DET-002', 'DET-003', 'DET-004', 'DET-005', 'DET-006'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    dimensions JSONB NOT NULL,
    affected_entities JSONB NOT NULL,
    observed_values JSONB NOT NULL,
    baseline JSONB NOT NULL,
    threshold_rule TEXT NOT NULL,
    evidence_references JSONB NOT NULL,
    explanation TEXT NOT NULL,
    detector_version TEXT NOT NULL,
    incident_key CHAR(64) NOT NULL UNIQUE,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS semantic_incidents_filter_idx
    ON semantic_incidents (status, severity, detector_type, last_detected_at DESC);
