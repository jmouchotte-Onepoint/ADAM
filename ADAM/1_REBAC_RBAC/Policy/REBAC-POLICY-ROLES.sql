-- 1. INSERT
DROP POLICY IF EXISTS policy_insert_roles ON roles;
CREATE POLICY policy_insert_roles
    ON roles
    FOR INSERT
    WITH CHECK (
        fn_check_model_condition(
            'ROLES',
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
DROP POLICY IF EXISTS policy_select_roles ON roles;
CREATE POLICY policy_select_roles
    ON roles
    FOR SELECT
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 3. DELETE
DROP POLICY IF EXISTS policy_delete_roles ON roles;
CREATE POLICY policy_delete_roles
    ON roles
    FOR DELETE
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);
