CREATE OR REPLACE FUNCTION fn_check_model_condition(
    p_relation_type enum_relations_roles_permissions,
    p_user_type text,
    p_user_id text,
    p_relation text,
    p_object_type text,
    p_object_id text,
    p_model_id uuid DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_condition text;
    v_relation_id UUID;
BEGIN
    -- 1. Si le model_id est connu (triggers), on prend exactement cette règle.
    IF p_model_id IS NOT NULL THEN
        SELECT m.condition
        INTO v_condition
        FROM model m
        WHERE m.id = p_model_id
        LIMIT 1;
    ELSE
        -- 2. Fallback (policies): s'il existe au moins un modèle sans condition,
        -- on ne force pas de relation conditionnelle.
        IF EXISTS (
            SELECT 1
            FROM model m
            WHERE m.user_type = p_user_type
                AND m.relation = p_relation
                AND m.object_type = p_object_type
                AND m.relation_type = p_relation_type
                AND m.condition IS NULL
        ) THEN
            RETURN '00000000-0000-0000-0000-000000000000'::UUID;
        END IF;

        -- Sinon, on récupère une condition explicite.
        SELECT m.condition
        INTO v_condition
        FROM model m
        WHERE m.user_type = p_user_type
            AND m.relation = p_relation
            AND m.object_type = p_object_type
            AND m.relation_type = p_relation_type
            AND m.condition IS NOT NULL
        LIMIT 1;
    END IF;

    -- 3. Pas de condition = autorisation directe (fast path)
    IF v_condition IS NULL THEN
        -- UUID nil pour signaler "autorisé sans relation conditionnelle"
        RETURN '00000000-0000-0000-0000-000000000000'::UUID;
    END IF;

    -- 4. Retourne l'ID de la relation conditionnelle si elle existe.
    -- Priorité 1: condition sur le même objet cible (ex: utilisateur#salarie sur entreprise).
    -- Priorité 2: condition portée par l'utilisateur lui-même (ex: users#doctor).
    SELECT rel.id
    INTO v_relation_id
    FROM relations rel
    WHERE rel.relation = v_condition
        AND rel.user_type = p_user_type
        AND rel.user_id = p_user_id
        AND (
            (rel.object_type = p_object_type AND rel.object_id = p_object_id)
            OR
            (rel.object_type = p_user_type AND rel.object_id = p_user_id)
        )
    ORDER BY CASE
        WHEN rel.object_type = p_object_type AND rel.object_id = p_object_id THEN 0
        ELSE 1
    END
    LIMIT 1;

    -- 5. Bloque si aucune relation conditionnelle n'est trouvée
    IF v_relation_id IS NULL THEN
        RAISE EXCEPTION '[P20001] Condition relationnelle non satisfaite - relation_type: %, user: %:%, relation: %, object: %:%, condition: %',
            p_relation_type, p_user_type, p_user_id, p_relation, p_object_type, p_object_id, v_condition;
    END IF;
    
    RETURN v_relation_id;
END;
$$ LANGUAGE plpgsql STABLE;