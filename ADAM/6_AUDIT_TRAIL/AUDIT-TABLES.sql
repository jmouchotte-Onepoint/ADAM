-- 1. Registre des tables couvertes par le journal
-- Rempli par le balayage du catalogue (voir Trigger/AUDIT-TRIGGER-ATTACH.sql).
-- Une table crée après ce changeset n'y figure pas tant qu'il n'est pas rejoué.
CREATE TABLE IF NOT EXISTS audit_coverage (
    table_name TEXT PRIMARY KEY,
    attached_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 2. Tête de chaîne, une par tenant
CREATE TABLE IF NOT EXISTS audit_chain_head (
    tenant_id VARCHAR(36) PRIMARY KEY,
    last_hash BYTEA NOT NULL,
    entries BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- 3. Journal des écritures d'autorisation
-- '*' regroupe les objets sans tenant propre (model, tenants).
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL DEFAULT '*',
    occurred_at TIMESTAMPTZ NOT NULL,
    transaction_id BIGINT NOT NULL,
    principal TEXT NOT NULL,
    subject TEXT,
    session_role TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE', 'DECISION')),
    object_table TEXT NOT NULL,
    row_id TEXT,
    before_row JSONB,
    after_row JSONB,
    details JSONB,
    previous_hash BYTEA NOT NULL,
    entry_hash BYTEA NOT NULL
);

-- 4. Lecture
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_id ON audit_log (tenant_id, id);
CREATE INDEX IF NOT EXISTS idx_audit_log_object ON audit_log (object_table, row_id);
