CREATE OR REPLACE FUNCTION fn_check_all_rules_from_view(
    p_id UUID,
    p_relation_type TEXT,
    p_user_attributes JSONB
)

RETURNS BOOLEAN AS $$
BEGIN

    RETURN NOT EXISTS (
        SELECT 1
          FROM view_all_access_rules
         WHERE id = p_id
           AND relation_type = p_relation_type
           AND NOT fn_check_dynamic_rules(rule_id, p_user_attributes)
    );
END;
-- SECURITY INVOKER : les vues étant en security_invoker, l'évaluation n'a
-- plus besoin des droits du propriétaire (A01-4/7).
$$ LANGUAGE plpgsql SECURITY INVOKER STABLE PARALLEL SAFE COST 10000;