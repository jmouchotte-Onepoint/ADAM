CREATE OR REPLACE FUNCTION fn_check_all_attributes_from_view(
    p_id UUID,
    p_relation_type TEXT,
    p_user_attributes JSONB
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Rejette tout type de relation inconnu plutôt que d'autoriser par défaut
    IF p_relation_type IS NULL OR lower(p_relation_type) NOT IN ('relations', 'roles', 'permissions') THEN
        RAISE EXCEPTION 'Unsupported relation type for attribute checks: %', p_relation_type;
    END IF;

    RETURN NOT EXISTS (
        SELECT 1
          FROM view_all_access_attributes
         WHERE id = p_id
           AND relation_type = lower(p_relation_type)
           AND fn_check_attributes(p_user_attributes, attribute) IS NOT TRUE
    );
END;
-- SECURITY INVOKER : les vues étant en security_invoker, l'évaluation n'a
-- plus besoin des droits du propriétaire (A01-4/7).
$$ LANGUAGE plpgsql SECURITY INVOKER STABLE PARALLEL SAFE COST 10000;
