-- 1. Table
ALTER TABLE model_rules ENABLE ROW LEVEL SECURITY;
-- dynamic_rules porte du SQL exécuté en SECURITY DEFINER : RLS sans politique
-- d'écriture, donc les écritures restent au propriétaire (A01-5).
ALTER TABLE dynamic_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS policy_select_dynamic_rules ON dynamic_rules;
CREATE POLICY policy_select_dynamic_rules
    ON dynamic_rules
    FOR SELECT
    USING (get_current_user_id() IS NOT NULL);
ALTER TABLE relations_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions_rules ENABLE ROW LEVEL SECURITY;