CREATE OR REPLACE FUNCTION adam.fn_recursive_insert_roles_permissions(
    p_deep INT,
    p_id UUID,
    p_user_type TEXT,
    p_user_id TEXT,
    p_relation TEXT,
    p_relation_type adam.enum_relations_roles_permissions,
    p_object_type TEXT,
    p_object_id TEXT,
    p_tenant_id TEXT,
    p_model_id UUID,
    p_parent_role_id UUID,
    p_parent_relation_id UUID,
    p_ancestor_relation_id UUID
) 
RETURNS VOID AS $$
DECLARE
    v_max_deep INT := 5;
BEGIN

    -- ============================================
    -- CTE récursif : propagation descendante (BASE 1 + BASE 2)
    -- ============================================
    WITH RECURSIVE adam_tree AS (

        -- ============================================
        -- BASE 0 : New Elements
        -- ============================================
        SELECT
            p_deep AS deep,
            p_id AS id,
            p_user_type AS user_type,
            p_user_id AS user_id,
            p_relation AS relation,
            p_relation_type AS relation_type,
            p_object_type AS object_type,
            p_object_id AS object_id,
            p_model_id AS model_id,
            p_parent_relation_id AS parent_relation_id,
            p_ancestor_relation_id AS ancestor_relation_id,
            p_parent_role_id AS parent_role_id

        UNION ALL

        -- ============================================
        -- BASE 1 : Règles directes
        -- ============================================
        SELECT
            p_deep + 1 AS deep,
            uuidv7(),
            p_user_type,
            p_user_id,
            m.relation,
            m.relation_type,
            p_object_type,
            p_object_id,
            m.id,
            p_parent_relation_id,
            p_ancestor_relation_id,
            p_parent_role_id
        FROM adam.model m
        WHERE m.object_type = p_object_type
            AND m.user_type = p_user_type
            AND m.relation_source = p_relation
            AND m.relation_origin IS NULL
            AND m.relation_type IN ('ROLES','PERMISSIONS')

        UNION ALL

        -- ============================================
        -- BASE 2 : Rôles existants (pour propagation descendante)
        -- Exemple: user_X [admin] org_Z existait, NEW crée org_Z parent→ doc_Y
        -- → Propage user_X [view] doc_Y
        -- ============================================        
        SELECT
            ro.deep + 1 AS deep,
            uuidv7() AS id,
            ro.user_type,
            ro.user_id,
            m.relation,
            m.relation_type,
            p_object_type,
            p_object_id,
            m.id,
            p_parent_relation_id,
            ro.parent_relation_id,
            ro.id AS parent_role_id
        FROM adam.roles ro
        INNER JOIN adam.model m
            ON m.relation_source = ro.relation
            AND m.relation_origin = p_relation
            AND m.object_type = p_object_type
            AND m.user_type = p_user_type
            AND m.relation_type IN ('ROLES','PERMISSIONS')
        WHERE ro.object_type = p_user_type
            AND ro.object_id = p_user_id
            AND ro.tenant_id = p_tenant_id

        UNION ALL

        -- ============================================
        -- BASE 3 : Relations "amont" déjà existantes
        -- Exemple: rel_A (user_X member→ group_G) existe
        --      NEW crée rel_B (group_G parent→ doc_Y)
        --      Règle: member + parent → view
        -- → Crée user_X [view] doc_Y (via group_G)
        -- ============================================
        SELECT
            rel.deep + 1 AS deep,
            rel.id AS id,
            rel.user_type,
            rel.user_id,
            m.relation_source,
            'RELATIONS',
            rel.object_type,
            rel.object_id,
            m.id,
            rel.id,
            NULL::uuid,
            NULL::uuid
        FROM adam.relations rel
        INNER JOIN adam.model m
            ON m.relation_source = rel.relation
            AND m.relation_origin = p_relation
            AND m.object_type = p_object_type
            AND m.user_type = p_user_type
            AND m.relation_type IN ('ROLES','PERMISSIONS')
        WHERE rel.object_type = p_user_type
            AND rel.object_id = p_user_id
            AND rel.tenant_id = p_tenant_id

        UNION ALL

        -- ============================================
        -- RECURSIVE : Propagation en cascade
        -- ============================================
        SELECT DISTINCT
            t.deep + 1,
            uuidv7(),
            t.user_type,
            t.user_id,
            m.relation,
            m.relation_type,
            rel.object_type,
            rel.object_id,
            m.id,
            rel.id,
            t.parent_relation_id,
            t.parent_role_id
        FROM adam_tree t
        INNER JOIN adam.relations rel
            ON rel.user_type = t.object_type
            AND rel.user_id = t.object_id
            AND rel.tenant_id = p_tenant_id
        INNER JOIN adam.model m
            ON m.relation_origin = rel.relation
            AND m.object_type = rel.object_type
            AND m.relation_source = t.relation
            AND m.user_type = t.object_type
            AND m.relation_type IN ('ROLES', 'PERMISSIONS')
        WHERE t.relation_type != 'PERMISSIONS' -- condition fin
            AND t.deep < v_max_deep -- garde de fou pour stack overflow
    ),
        
    -- ============================================
    -- INSERTS avec DISTINCT
    -- ============================================
    insert_roles AS (
        INSERT INTO adam.roles (
            id, deep, user_type, user_id, relation, 
            object_type, object_id, tenant_id, model_id,
            parent_role_id, parent_relation_id, ancestor_relation_id,
            is_auto_generated
        )
        SELECT
            id, deep, user_type, user_id, relation,
            object_type, object_id, p_tenant_id, model_id,
            parent_role_id, parent_relation_id, ancestor_relation_id,
            true
        FROM adam_tree
        WHERE relation_type = 'ROLES'
        ON CONFLICT DO NOTHING
        RETURNING true
    )

    INSERT INTO adam.permissions (
        id, deep, user_type, user_id, relation,
        object_type, object_id, tenant_id, model_id,
        parent_role_id, parent_relation_id, ancestor_relation_id,
        is_auto_generated
    )
    SELECT
        id, deep, user_type, user_id, relation,
        object_type, object_id, p_tenant_id, model_id,
        parent_role_id, parent_relation_id, ancestor_relation_id,
        true
    FROM adam_tree
    WHERE relation_type = 'PERMISSIONS'
    ON CONFLICT DO NOTHING;
END;
$$ LANGUAGE plpgsql;