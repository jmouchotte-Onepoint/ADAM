-- 1. Journalisation d'une décision depuis l'applicatif
-- Seule entrée ouverte à l'appelant, et elle ne produit que des entrées
-- 'DECISION'. L'évaluation RLS ne l'appelle pas : une politique SELECT ne peut
-- pas écrire, donc une décision n'est tracée que si l'appelant le demande.
CREATE OR REPLACE FUNCTION fn_log_decision(
    p_object_type TEXT, p_object_id TEXT, p_operation TEXT,
    p_allowed BOOLEAN, p_reason JSONB DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tenant TEXT;
    v_principal TEXT := CASE
        WHEN system_user LIKE 'oauth:%' THEN substring(system_user FROM 7)
        ELSE session_user::text
    END;
BEGIN
    SELECT tenant_id INTO v_tenant
      FROM tenants_per_users
     WHERE pg_user = v_principal
       AND tenant_id = current_setting('app.adam.tenant_id', true)
     LIMIT 1;

    RETURN fn_audit_append(
        v_tenant, 'DECISION', p_object_type, p_object_id, NULL, NULL,
        jsonb_build_object('operation', p_operation, 'allowed', p_allowed,
                           'reason', p_reason)
    );
END;
$$;
