-- 1. Insert
CREATE POLICY policy_insert_roles_rules
    ON adam.roles_rules
    FOR INSERT
    WITH CHECK (
        role_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_roles_rules
    ON adam.roles_rules
    FOR SELECT
    USING (
        role_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Delete
CREATE POLICY policy_delete_roles_rules
    ON adam.roles_rules
    FOR DELETE
    USING (
        adam.is_allow('delete')
        AND adam.get_current_user_id() IS NOT NULL
);
