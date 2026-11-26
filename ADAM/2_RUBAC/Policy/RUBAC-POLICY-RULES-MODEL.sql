-- 1. Insert
DROP POLICY IF EXISTS policy_insert_model_policy_rules ON model_rules;
CREATE POLICY policy_insert_model_policy_rules
    ON model_rules
    FOR INSERT
    WITH CHECK (
        model_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 2. Select
DROP POLICY IF EXISTS policy_select_model_policy_rules ON model_rules;
CREATE POLICY policy_select_model_policy_rules
    ON model_rules
    FOR SELECT
    USING (
        model_id IS NOT NULL
        AND (SELECT get_current_user_id()) IS NOT NULL
);

-- 2. Delete
DROP POLICY IF EXISTS policy_delete_model_policy_rules ON model_rules;
CREATE POLICY policy_delete_model_policy_rules
    ON model_rules
    FOR DELETE
    USING (
        is_allow('delete')
        AND (SELECT get_current_user_id()) IS NOT NULL
);
