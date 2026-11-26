-- 1. INSERT
DROP POLICY IF EXISTS policy_insert_relations ON relations;
CREATE POLICY policy_insert_relations
    ON relations
    FOR INSERT
    WITH CHECK (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 2. SELECT
DROP POLICY IF EXISTS policy_select_relations ON relations;
CREATE POLICY policy_select_relations
    ON relations
    FOR SELECT
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 3. DELETE
DROP POLICY IF EXISTS policy_delete_relations ON relations;
CREATE POLICY policy_delete_relations
    ON relations
    FOR DELETE
    USING (
        tenant_id = (SELECT get_current_tenant_id())
        AND (SELECT get_current_user_id()) IS NOT NULL
);
