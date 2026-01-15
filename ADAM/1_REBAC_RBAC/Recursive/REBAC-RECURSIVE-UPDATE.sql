CREATE OR REPLACE FUNCTION adam.fn_recursive_update_roles_permissions_with_model(
    p_model_id UUID
)
RETURNS VOID AS $$
DECLARE
    v_model_relation_source TEXT;
    v_model_user_type TEXT;
    v_model_relation TEXT;
    v_model_object_type TEXT;
    v_model_relation_origin TEXT;
    v_model_relation_source_type adam.enum_relations_roles_permissions;
    v_model_relation_type adam.enum_relations_roles_permissions;
BEGIN

    -- ============================================
    -- MODEL: Récuperation des infos du model
    -- ============================================
    SELECT 
        m.relation_source,
        m.relation_source_type,
        m.user_type,
        m.relation,
        m.relation_type,
        m.object_type,
        m.relation_origin
    INTO 
        v_model_relation_source,
        v_model_relation_source_type,
        v_model_user_type,
        v_model_relation,
        v_model_relation_type,
        v_model_object_type,
        v_model_relation_origin
    FROM adam.model AS m
    WHERE m.id = p_model_id;

    -- ============================================
    -- CTE : Propagation du nouveau model
    -- ============================================
    WITH adam_tree AS (

        -- ============================================
        -- RELATIONS : Propagation direct
        -- ============================================
        SELECT
            rel.deep + 1 AS deep,
            uuidv7() AS id,
            v_model_user_type AS user_type,
            rel.user_id AS user_id,
            v_model_relation AS relation,
            v_model_relation_type AS relation_type,
            v_model_object_type AS object_type,
            rel.object_id AS object_id,
            rel.tenant_id AS tenant_id,
            p_model_id AS model_id,
            rel.id AS parent_relation_id,
            NULL::uuid AS ancestor_relation_id,
            NULL::uuid AS parent_role_id
        FROM adam.relations AS rel
        WHERE rel.user_type = v_model_user_type
            AND rel.relation = v_model_relation_source
            AND rel.object_type = v_model_object_type
            AND v_model_relation_source_type = 'RELATIONS'
            AND v_model_relation_type IN ('ROLES','PERMISSIONS')
            AND v_model_relation_origin IS NULL

        UNION ALL

        -- ============================================
        -- RELATIONS : Propagation avec héritage
        -- ============================================
        SELECT 
            rel2.deep + 2 AS deep, --> ancestor_relation_id not null
            uuidv7() AS id,
            rel2.user_type AS user_type,
            rel2.user_id AS user_id,
            v_model_relation AS relation,
            v_model_relation_type AS relation_type,
            rel1.object_type AS object_type,
            rel1.object_id AS object_id,
            rel2.tenant_id AS tenant_id,
            p_model_id AS model_id,
            rel2.id AS parent_relation_id,
            rel1.id AS ancestor_relation_id,
            NULL AS parent_role_id
	    FROM adam.relations AS rel1 -- objectif / object
            JOIN adam.relations AS rel2 -- source / user
                ON rel2.object_id = rel1.user_id
                AND rel2.object_type = rel1.user_type
                AND rel2.tenant_id = rel1.tenant_id
                AND rel2.relation = v_model_relation_source
            WHERE rel1.relation = v_model_relation_origin
                AND rel1.user_type = v_model_user_type
                AND rel1.object_type = v_model_object_type
                AND v_model_relation_source_type = 'RELATIONS'
                AND v_model_relation_type IN ('ROLES','PERMISSIONS')

        UNION ALL

        -- ============================================
        -- ROLES : Propagation direct
        -- ============================================
        SELECT
            r.deep + 1,
            uuidv7(),
            v_model_user_type,
            r.user_id,
            v_model_relation,
            v_model_relation_type,
            v_model_object_type,
            r.object_id,
            r.tenant_id,
            p_model_id,
            r.parent_relation_id,
            r.ancestor_relation_id,
            r.id
        FROM adam.roles AS r
        WHERE r.user_type = v_model_user_type
            AND r.relation = v_model_relation_source
            AND r.object_type = v_model_object_type
            AND v_model_relation_source_type = 'ROLES'
            AND v_model_relation_type IN ('ROLES','PERMISSIONS')
            AND v_model_relation_origin IS NULL

        UNION ALL

        -- ============================================
        -- ROLES : Propagation indirect
        -- ============================================
        SELECT 
            r.deep + 1,
            uuidv7(),
            r.user_type,
            r.user_id,
            v_model_relation,
            v_model_relation_type,
            rel.object_type,
            rel.object_id,
            r.tenant_id,
            p_model_id,
            rel.id,
            r.parent_relation_id,
            r.id
        FROM adam.relations AS rel -- objectif / object
            JOIN adam.roles AS r -- source / user
                ON r.object_id = rel.user_id
                AND r.object_type = rel.user_type
                AND r.tenant_id = rel.tenant_id
                AND r.relation = v_model_relation_source
            WHERE rel.relation = v_model_relation_origin
                AND rel.user_type = v_model_user_type
                AND rel.object_type = v_model_object_type
                AND v_model_relation_source_type = 'ROLES'
                AND v_model_relation_type IN ('ROLES','PERMISSIONS')
    ),
        
    -- ============================================
    -- INSERTS avec DISTINCT
    -- ============================================
    insert_roles AS (
        INSERT INTO adam.roles (
            id, deep, user_type, user_id, relation, 
            object_type, object_id, tenant_id, model_id,
            parent_role_id, parent_relation_id, ancestor_relation_id
        )
        SELECT
            id, deep, user_type, user_id, relation,
            object_type, object_id, tenant_id, model_id,
            parent_role_id, parent_relation_id, ancestor_relation_id
        FROM adam_tree
        WHERE relation_type = 'ROLES'
        ON CONFLICT DO NOTHING
        RETURNING true
    )

    INSERT INTO adam.permissions (
        id, deep, user_type, user_id, relation,
        object_type, object_id, tenant_id, model_id,
        parent_role_id, parent_relation_id, ancestor_relation_id    
    )
    SELECT
        id, deep, user_type, user_id, relation,
        object_type, object_id, tenant_id, model_id,
        parent_role_id, parent_relation_id, ancestor_relation_id
    FROM adam_tree
    WHERE relation_type = 'PERMISSIONS'
    ON CONFLICT DO NOTHING;

END;
$$ LANGUAGE plpgsql;