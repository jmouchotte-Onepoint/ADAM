-- 1. INSERT
DROP POLICY IF EXISTS policy_insert_permissions ON permissions;
CREATE POLICY policy_insert_permissions
    ON permissions
    FOR INSERT
    WITH CHECK (
        fn_check_model_condition(
            'PERMISSIONS',
            user_type,
            user_id,
            relation,
            object_type,
            object_id
        ) IS NOT NULL
        AND tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 2. SELECT
DROP POLICY IF EXISTS policy_select_permissions ON permissions;
CREATE POLICY policy_select_permissions
    ON permissions
    FOR SELECT
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 3. DELETE
DROP POLICY IF EXISTS policy_delete_permissions ON permissions;
CREATE POLICY policy_delete_permissions
    ON permissions
    FOR DELETE
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);
