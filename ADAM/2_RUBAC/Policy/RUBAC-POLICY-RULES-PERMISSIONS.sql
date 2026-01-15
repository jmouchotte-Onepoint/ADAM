-- 1. Insert
CREATE POLICY policy_insert_permissions_rules
    ON adam.permissions_rules
    FOR INSERT
    WITH CHECK (
        permission_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_permissions_rules
    ON adam.permissions_rules
    FOR SELECT
    USING (
        permission_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Delete
CREATE POLICY policy_delete_permissions_rules
    ON adam.permissions_rules
    FOR DELETE
    USING (
        adam.is_allow('delete')
        AND adam.get_current_user_id() IS NOT NULL
);
