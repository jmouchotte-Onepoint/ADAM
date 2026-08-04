-- 1. INSERT
CREATE POLICY policy_insert_relations
    ON relations
    FOR INSERT
    WITH CHECK (
        tenant_id = get_current_tenant_id()
        AND get_current_user_id() IS NOT NULL
);

-- 2. SELECT
CREATE POLICY policy_select_relations
    ON relations
    FOR SELECT
    USING (
        tenant_id = get_current_tenant_id()
        AND get_current_user_id() IS NOT NULL
);

-- 3. DELETE
CREATE POLICY policy_delete_relations
    ON relations
    FOR DELETE
    USING (
        tenant_id = get_current_tenant_id()
        AND get_current_user_id() IS NOT NULL
);