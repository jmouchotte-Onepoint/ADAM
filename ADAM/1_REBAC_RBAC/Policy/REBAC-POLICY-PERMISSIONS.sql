-- 1. INSERT
CREATE POLICY policy_insert_permissions
    ON adam.permissions
    FOR INSERT
    WITH CHECK (
        adam.fn_check_model_condition(
            'PERMISSIONS',
            user_type,
            user_id,
            relation,
            object_type,
            object_id
        )
        AND tenant_id = adam.get_current_tenant_id()
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. SELECT
CREATE POLICY policy_select_permissions
    ON adam.permissions
    FOR SELECT
    USING (
        tenant_id = adam.get_current_tenant_id()
        AND adam.get_current_user_id() IS NOT NULL
);

-- 3. DELETE
CREATE POLICY policy_delete_permissions
    ON adam.permissions
    FOR DELETE
    USING (
        tenant_id = adam.get_current_tenant_id()
        AND adam.get_current_user_id() IS NOT NULL
);