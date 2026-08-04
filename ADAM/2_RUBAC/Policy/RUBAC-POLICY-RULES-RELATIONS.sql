-- 1. Insert
CREATE POLICY policy_insert_relations_rules
    ON relations_rules
    FOR INSERT
    WITH CHECK (
        relation_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_relations_rules
    ON relations_rules
    FOR SELECT
    USING (
        relation_id IS NOT NULL
        AND get_current_user_id() IS NOT NULL
);

-- 2. Delete
CREATE POLICY policy_delete_relations_rules
    ON relations_rules
    FOR DELETE
    USING (
        is_allow('delete')
        AND get_current_user_id() IS NOT NULL
);
