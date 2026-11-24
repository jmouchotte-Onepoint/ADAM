-- 1. Trigger générique
-- Le tenant et l'id sont lus dans la ligne quand elle les porte : les tables du
-- schéma n'ont pas toutes une colonne id ni une colonne tenant_id.
CREATE OR REPLACE FUNCTION fn_audit_row()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_before JSONB := CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END;
    v_after JSONB := CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END;
    v_row JSONB := COALESCE(v_after, v_before);
BEGIN
    PERFORM fn_audit_append(
        v_row ->> 'tenant_id', TG_OP, TG_TABLE_NAME, v_row ->> 'id',
        v_before, v_after, NULL
    );
    RETURN NULL;
END;
$$;

REVOKE ALL ON FUNCTION fn_audit_row() FROM PUBLIC;
