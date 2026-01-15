CREATE OR REPLACE FUNCTION adam.fn_check_attributes(
    p_users_attributes jsonb,
    p_rules_attributes jsonb
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_attribute_value text;
    v_rule jsonb;
    v_key text;
    v_value jsonb;
    v_operator text;
BEGIN

    -- Vérifier si non null
    IF p_rules_attributes IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Parcours de chaque JSON dans la liste
    FOR v_rule IN SELECT * FROM jsonb_array_elements(p_rules_attributes)
        LOOP
            v_key := v_rule ->>'key';
            v_operator := v_rule ->>'operator';
            v_value := v_rule ->'value';

            -- Récupère la valeur utilisateur pour cette clé
            v_user_attribute_value := p_users_attributes->>v_key;

            -- Si l'utilisateur n'a pas cet attribut
            IF v_user_attribute_value IS NULL THEN
                RAISE DEBUG 'L''attribut "%" est NULL ou absent', v_key;
                RETURN FALSE;
            END IF;

            -- Évaluation selon l'opérateur et le type
            BEGIN
                -- Opérateur "IS" (égalité stricte)
                IF v_operator = 'IS' THEN
                    IF v_user_attribute_value <> v_value->>0 THEN
                        RETURN FALSE;
                    END IF;
                    -- Opérateur "SUP" (supérieur à)
                ELSIF v_operator = 'SUP' THEN
                    IF v_user_attribute_value <= v_value->>0 THEN
                        RETURN FALSE;
                    END IF;
                    -- Opérateur "INF" (inférieur à)
                ELSIF v_operator = 'INF' THEN
                    IF v_user_attribute_value >= v_value->>0 THEN
                        RETURN FALSE;
                    END IF;
                    -- Opérateur "IN" (valeur dans un tableau)
                ELSIF v_operator = 'IN' THEN
                    IF NOT v_value::jsonb ? v_user_attribute_value THEN
                        RETURN FALSE;
                    END IF;
                    -- Opérateur "BETWEEN" (entre deux valeurs)
                ELSIF v_operator = 'BETWEEN' THEN
                    IF v_user_attribute_value < v_value->>0 OR v_user_attribute_value > v_value->>1 THEN
                        RETURN FALSE;
                    END IF;
                    -- Opérateur inconnu
                ELSE
                    RAISE WARNING 'Opérateur inconnu pour l''attribut "%": "%"', v_key, v_operator;
                    RETURN FALSE;
                END IF;

            EXCEPTION WHEN OTHERS THEN
                RAISE EXCEPTION 'Erreur lors de l''évaluation de l''attribut "%": %', v_key, SQLERRM;
                RETURN FALSE;
            END;

        END LOOP;
    -- Toutes les conditions sont validées
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;