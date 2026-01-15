CREATE OR REPLACE FUNCTION adam.fn_check_model_condition(
    p_relation_type adam.enum_relations_roles_permissions,
    p_user_type text,
    p_user_id text,
    p_relation text,
    p_object_type text,
    p_object_id text
) RETURNS boolean AS $$
DECLARE
    v_condition text;
    v_result boolean;
BEGIN

    -- 1. Récupère la condition en une seule requête optimisée
    SELECT m.condition
    INTO v_condition
    FROM adam.model m
    WHERE m.user_type = p_user_type
        AND m.relation = p_relation
        AND m.object_type = p_object_type
        AND m.relation_type = p_relation_type
        AND m.condition IS NOT NULL
    LIMIT 1;

    -- 2. Pas de condition = autorisation directe (fast path)
    IF v_condition IS NULL THEN
        RETURN TRUE;
    END IF;

    -- 3. Vérifie l'existence en une seule requête avec EXISTS
    SELECT EXISTS (
        SELECT 1
        FROM adam.relations rel
        WHERE rel.relation = v_condition
            AND rel.object_id = p_user_id
            AND rel.object_type = p_user_type
            AND rel.user_id = p_user_id
    ) INTO v_result;

    -- 4. Log si le résultat est FALSE
    IF NOT v_result THEN
        RAISE DEBUG 'check_model_condition returned FALSE - relation_type: %, user: %:%, relation: %, object: %:%, condition: %',
            p_relation_type, p_user_type, p_user_id, p_relation, p_object_type, p_object_id, v_condition;
    END IF;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql STABLE;