-- 1. Insert
DROP POLICY IF EXISTS policy_insert_permissions_attributes ON permissions_attributes;
CREATE POLICY policy_insert_permissions_attributes
    ON permissions_attributes
    FOR INSERT
    WITH CHECK (
        permission_id IS NOT NULL
        AND get_current_user_id() IS NOT NULL
);

-- 2. Select : une ligne de métadonnée n'est visible que si sa ligne
-- parente l'est, ce qui lui transmet le filtrage de tenant (A01-7).
DROP POLICY IF EXISTS policy_select_permissions_attributes ON permissions_attributes;
CREATE POLICY policy_select_permissions_attributes
    ON permissions_attributes
    FOR SELECT
    USING (
        get_current_user_id() IS NOT NULL
        AND EXISTS (SELECT 1 FROM permissions AS parent WHERE parent.id = permission_id)
);

-- 2. Delete
DROP POLICY IF EXISTS policy_delete_permissions_attributes ON permissions_attributes;
CREATE POLICY policy_delete_permissions_attributes
    ON permissions_attributes
    FOR DELETE
    USING (
        is_allow('delete')
        AND get_current_user_id() IS NOT NULL
);