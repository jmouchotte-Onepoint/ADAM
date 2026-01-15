CREATE OR REPLACE FUNCTION adam.fn_check_all_attributes_from_view(
    p_id UUID,
    p_relation_type TEXT,
    p_user_attributes JSONB
)
RETURNS BOOLEAN AS $$
DECLARE
    v_record RECORD;
BEGIN

    -- Parcourt toutes les règles pour cette permission depuis la table paramétrable
    FOR v_record IN EXECUTE 'SELECT * FROM adam.view_all_access_attributes WHERE id = $1 AND relation_type = $2' USING p_id, p_relation_type
        LOOP
            -- Vérifie les attributs
            IF NOT adam.fn_check_attributes(p_user_attributes, v_record.attributes) THEN
                RETURN FALSE;
            END IF;
        END LOOP;

    -- Si aucune règle trouvée ou toutes validées → accès autorisé
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;