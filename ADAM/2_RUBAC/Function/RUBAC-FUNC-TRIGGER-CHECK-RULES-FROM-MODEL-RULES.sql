CREATE OR REPLACE FUNCTION adam.fn_trigger_check_rules_from_model()
RETURNS TRIGGER AS $$
DECLARE
    v_model_rule RECORD;
BEGIN

    -- Parcourt toutes les règles pour la règle depuis la table paramétrable
    FOR v_model_rule IN EXECUTE 'SELECT * FROM adam.model_rules WHERE model_id = $1' USING NEW.model_id
        LOOP
            -- Replace uniquement les 2 paramètres variables utiles
            v_model_rule.params := jsonb_set(v_model_rule.params, '{idDossier}', to_jsonb(NEW.object_id), false);
            v_model_rule.params := jsonb_set(v_model_rule.params, '{user_id}', to_jsonb(NEW.user_id), false);

            -- Vérifie les attributs
            IF NOT adam.fn_check_dynamic_rules(v_model_rule.rule_id, v_model_rule.params) THEN
                RAISE DEBUG 'La règle id = % n''est pas validée pour les paramètres : %', v_model_rule.rule_id, v_model_rule.params::jsonb;
                RETURN NULL;
            END IF;

        END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;