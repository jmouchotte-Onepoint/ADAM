-- 1. Insert
DROP POLICY IF EXISTS policy_insert_relations_rules ON relations_rules;
CREATE POLICY policy_insert_relations_rules
    ON relations_rules
    FOR INSERT
    WITH CHECK (
        relation_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND get_current_user_id() IS NOT NULL
);

-- 2. Select : une ligne de métadonnée n'est visible que si sa ligne
-- parente l'est, ce qui lui transmet le filtrage de tenant (A01-7).
DROP POLICY IF EXISTS policy_select_relations_rules ON relations_rules;
CREATE POLICY policy_select_relations_rules
    ON relations_rules
    FOR SELECT
    USING (
        get_current_user_id() IS NOT NULL
        AND EXISTS (SELECT 1 FROM relations AS parent WHERE parent.id = relation_id)
);

-- 2. Delete
DROP POLICY IF EXISTS policy_delete_relations_rules ON relations_rules;
CREATE POLICY policy_delete_relations_rules
    ON relations_rules
    FOR DELETE
    USING (
        is_allow('delete')
        AND get_current_user_id() IS NOT NULL
);
