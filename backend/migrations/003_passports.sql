CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY,
    identifier TEXT NOT NULL UNIQUE,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS passports (
    id UUID PRIMARY KEY,
    product_id UUID NOT NULL UNIQUE REFERENCES products(id),
    current_version INTEGER NOT NULL DEFAULT 1 CHECK (current_version > 0),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS passport_versions (
    passport_id UUID NOT NULL REFERENCES passports(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version > 0),
    graph_uri TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (passport_id, version)
);

CREATE INDEX IF NOT EXISTS products_created_at_idx ON products (created_at DESC);
CREATE INDEX IF NOT EXISTS passports_created_at_idx ON passports (created_at DESC);
