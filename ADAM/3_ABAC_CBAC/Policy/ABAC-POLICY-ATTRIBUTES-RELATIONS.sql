-- 1. Insert
CREATE POLICY policy_insert_relations_attributes
    ON adam.relations_attributes
    FOR INSERT
    WITH CHECK (
        relation_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_relations_attributes
    ON adam.relations_attributes
    FOR SELECT
    USING (
        relation_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 3. Delete
CREATE POLICY policy_delete_relations_attributes
    ON adam.relations_attributes
    FOR DELETE
    USING (
        adam.is_allow('delete')
        AND adam.get_current_user_id() IS NOT NULL
);