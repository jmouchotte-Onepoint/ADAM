CREATE OR REPLACE FUNCTION fn_check_all_attributes_from_view(
    p_id UUID,
    p_relation_type TEXT,
    p_user_attributes JSONB
)
RETURNS BOOLEAN AS $$
DECLARE
    v_record RECORD;
BEGIN
    -- Rejette tout type de relation inconnu plutôt que d'autoriser par défaut
    IF p_relation_type IS NULL OR lower(p_relation_type) NOT IN ('relations', 'roles', 'permissions') THEN
        RAISE EXCEPTION 'Unsupported relation type for attribute checks: %', p_relation_type;
    END IF;

    -- Parcourt tous les attributs de cette relation depuis la vue
    FOR v_record IN
        SELECT attribute FROM view_all_access_attributes
        WHERE id = p_id AND relation_type = lower(p_relation_type)
    LOOP
        -- Vérifie les attributs
        IF fn_check_attributes(p_user_attributes, v_record.attribute) IS NOT TRUE THEN
            RETURN FALSE;
        END IF;
    END LOOP;

    -- Si aucun attribut trouvé ou tous validés → accès autorisé
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE PARALLEL SAFE;
