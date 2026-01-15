-- 1. Insert
CREATE POLICY policy_insert_roles_attributes
    ON adam.roles_attributes
    FOR INSERT
    WITH CHECK (
        role_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 2. Select
CREATE POLICY policy_select_roles_attributes
    ON adam.roles_attributes
    FOR SELECT
    USING (
        role_id IS NOT NULL
        AND adam.get_current_user_id() IS NOT NULL
);

-- 3. Delete
CREATE POLICY policy_delete_roles_attributes
    ON adam.roles_attributes
    FOR DELETE
    USING (
        adam.is_allow('delete')
        AND adam.get_current_user_id() IS NOT NULL
);