-- 1. Insert
DROP POLICY IF EXISTS policy_insert_permissions_rules ON permissions_rules;
CREATE POLICY policy_insert_permissions_rules
    ON permissions_rules
    FOR INSERT
    WITH CHECK (
        permission_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 2. Select : une ligne de métadonnée n'est visible que si sa ligne
-- parente l'est, ce qui lui transmet le filtrage de tenant (A01-7).
DROP POLICY IF EXISTS policy_select_permissions_rules ON permissions_rules;
CREATE POLICY policy_select_permissions_rules
    ON permissions_rules
    FOR SELECT
    USING (
        (SELECT get_current_user_id()) IS NOT NULL
        AND EXISTS (SELECT 1 FROM permissions AS parent WHERE parent.id = permission_id)
);

-- 2. Delete
DROP POLICY IF EXISTS policy_delete_permissions_rules ON permissions_rules;
CREATE POLICY policy_delete_permissions_rules
    ON permissions_rules
    FOR DELETE
    USING (
        is_allow('delete')
        AND (SELECT get_current_user_id()) IS NOT NULL
);
