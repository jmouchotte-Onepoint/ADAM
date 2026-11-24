-- 1. Lecture limitée au tenant courant
-- Les entrées globales ('*') ne sortent pas du propriétaire du schéma.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS policy_select_audit_log ON audit_log;
CREATE POLICY policy_select_audit_log
    ON audit_log
    FOR SELECT
    USING (tenant_id = get_current_tenant_id());

ALTER TABLE audit_chain_head ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS policy_select_audit_chain_head ON audit_chain_head;
CREATE POLICY policy_select_audit_chain_head
    ON audit_chain_head
    FOR SELECT
    USING (tenant_id = get_current_tenant_id());

-- 2. Pas de politique d'écriture : aucun GRANT ne permet d'écrire le journal,
-- seules les fonctions SECURITY DEFINER y insèrent.
