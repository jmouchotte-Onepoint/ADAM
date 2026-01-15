CREATE OR REPLACE FUNCTION adam.fn_check_dynamic_rules(
    p_rule_id UUID,
    p_users_attributes jsonb
) RETURNS BOOLEAN AS $$
DECLARE
    v_param text;
    v_user_attribute_value text;
    v_array_params text[];
    v_rule text;
    v_result BOOLEAN;
BEGIN

    -- Vérifier si non null
    IF p_rule_id IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Récupérer la condition et les clés
    SELECT dr.rule, dr.params
    INTO v_rule, v_array_params
    FROM adam.dynamic_rules AS dr
    WHERE dr.id = p_rule_id;

    -- Acune règle ne match
    IF v_rule IS NULL THEN
        RAISE WARNING 'Aucune règle trouve pour l''id : %', p_rule_id;
        RETURN TRUE;
    END IF;

    FOREACH v_param IN ARRAY v_array_params LOOP
        -- Extraire la valeur utilisateur
        v_user_attribute_value := quote_nullable(p_users_attributes->>v_param);
        IF v_user_attribute_value IS NULL THEN
            RAISE DEBUG 'Le paramètre "%" est NULL ou absent', v_param;
            RETURN FALSE;
        END IF;
        -- Appliquer le filtre
        v_rule := REPLACE(v_rule, '$' || v_param, v_user_attribute_value);
    END LOOP;

    -- Exécuter la requête finale
    EXECUTE v_rule INTO v_result;
    -- Renvoyer le résultat
    IF v_result IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;

