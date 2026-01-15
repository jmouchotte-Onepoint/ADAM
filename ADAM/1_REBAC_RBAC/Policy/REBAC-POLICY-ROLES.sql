-- 1. INSERT
CREATE POLICY policy_insert_roles
    ON adam.roles
    FOR INSERT
    WITH CHECK (
        adam.fn_check_model_condition(
            'ROLES',
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
CREATE POLICY policy_select_roles
    ON adam.roles
    FOR SELECT
    USING (
        tenant_id = adam.get_current_tenant_id()
        AND adam.get_current_user_id() IS NOT NULL
);

-- 3. DELETE
CREATE POLICY policy_delete_roles
    ON adam.roles
    FOR DELETE
    USING (
        tenant_id = adam.get_current_tenant_id()
        AND adam.get_current_user_id() IS NOT NULL
);
