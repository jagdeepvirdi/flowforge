-- FlowForge internal database schema
-- Apply with: psql -U flowforge -d flowforge -f flowforge/db/schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────
-- Lookup / config tables (no FK dependencies)
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ff_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,   -- bcrypt
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ff_recipient_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    addresses       TEXT[] NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ff_email_providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    provider_type   VARCHAR(20) NOT NULL CHECK (provider_type IN ('gmail', 'microsoft365', 'smtp')),
    config          TEXT NOT NULL,           -- AES-256-GCM encrypted JSON
    is_default      BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ff_db_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    db_type         VARCHAR(20) NOT NULL CHECK (db_type IN ('postgresql', 'oracle')),
    config          TEXT NOT NULL,           -- AES-256-GCM encrypted JSON
    is_default      BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- Config tables with FK dependencies
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ff_report_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    connection_id   UUID REFERENCES ff_db_connections(id) ON DELETE SET NULL,
    query           TEXT NOT NULL,
    format          VARCHAR(20) NOT NULL CHECK (format IN ('excel', 'csv', 'pdf')),
    template_path   VARCHAR(500),
    output_filename VARCHAR(500) NOT NULL,
    title           VARCHAR(255),
    sheet_name      VARCHAR(100),
    columns         TEXT[],
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ff_email_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    provider_id         UUID REFERENCES ff_email_providers(id) ON DELETE SET NULL,
    from_name           VARCHAR(255),
    subject             VARCHAR(500) NOT NULL,
    header_text         VARCHAR(500),
    body_template       TEXT NOT NULL,
    recipient_group_id  UUID REFERENCES ff_recipient_groups(id) ON DELETE SET NULL,
    to_addresses        TEXT[],
    cc_addresses        TEXT[],
    bcc_addresses       TEXT[],
    attachment_max_mb   INTEGER DEFAULT 10,
    drive_folder_id     VARCHAR(255),
    drive_share_message TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- Pipeline tables
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ff_pipelines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL UNIQUE,
    description     TEXT,
    schedule        VARCHAR(100),
    enabled         BOOLEAN DEFAULT true,
    timeout_minutes INTEGER DEFAULT 60,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ff_pipeline_steps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID NOT NULL REFERENCES ff_pipelines(id) ON DELETE CASCADE,
    step_order      INTEGER NOT NULL,
    name            VARCHAR(255) NOT NULL,
    step_type       VARCHAR(50) NOT NULL CHECK (step_type IN ('db_procedure', 'db_query', 'report', 'email', 'drive_upload', 'ai_analyze')),
    config          JSONB NOT NULL DEFAULT '{}',
    on_error        VARCHAR(20) DEFAULT 'stop' CHECK (on_error IN ('stop', 'continue')),
    enabled         BOOLEAN DEFAULT true,
    UNIQUE (pipeline_id, step_order)
);

CREATE TABLE IF NOT EXISTS ff_pipeline_variables (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID NOT NULL REFERENCES ff_pipelines(id) ON DELETE CASCADE,
    var_key         VARCHAR(100) NOT NULL,
    var_value       TEXT NOT NULL,
    is_secret       BOOLEAN DEFAULT false,
    UNIQUE (pipeline_id, var_key)
);

-- ─────────────────────────────────────────
-- Run history tables
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ff_pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID REFERENCES ff_pipelines(id) ON DELETE SET NULL,
    pipeline_name   VARCHAR(255) NOT NULL,
    status          VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'failed', 'cancelled')),
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMP,
    duration_ms     INTEGER,
    triggered_by    VARCHAR(50),
    error_step      VARCHAR(255),
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS ff_step_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES ff_pipeline_runs(id) ON DELETE CASCADE,
    step_name       VARCHAR(255) NOT NULL,
    step_type       VARCHAR(50) NOT NULL,
    step_order      INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'failed', 'skipped')),
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMP,
    duration_ms     INTEGER,
    rows_affected   INTEGER,
    output_path     VARCHAR(500),
    drive_url       VARCHAR(500),
    email_sent_to   TEXT[],
    logs            TEXT,
    error_message   TEXT
);

-- ─────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON ff_pipeline_runs(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at  ON ff_pipeline_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_step_runs_pipeline_run_id ON ff_step_runs(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_pipeline   ON ff_pipeline_steps(pipeline_id, step_order);

-- ─────────────────────────────────────────
-- Seed: default admin user (password: admin — change immediately)
-- password_hash for 'admin': $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/9a7a7T1.a
-- Generate your own: python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
-- ─────────────────────────────────────────

INSERT INTO ff_users (username, password_hash)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/9a7a7T1.a')
ON CONFLICT (username) DO NOTHING;
