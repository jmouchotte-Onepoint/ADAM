-- 1. Insert
CREATE POLICY policy_insert_model_policy_rules
    ON adam.model_rules
    FOR INSERT
    WITH CHECK (
        model_id IS NOT NULL
        AND rule_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_model_policy_rules
    ON adam.model_rules
    FOR SELECT
    USING (
        model_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Delete
CREATE POLICY policy_delete_model_policy_rules
    ON adam.model_rules
    FOR DELETE
    USING (
        adam.is_allow('delete')
        AND adam.get_current_user_id() IS NOT NULL
);
