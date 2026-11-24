-- 1. Vérification de la chaîne
-- SECURITY INVOKER : les chaînes étant par tenant, chacun vérifie la sienne de
-- bout en bout et le propriétaire les vérifie toutes. Aucun contenu d'entrée
-- n'est renvoyé, seulement le compte et l'id de la première rupture.
CREATE OR REPLACE FUNCTION fn_verify_audit_chain(p_tenant TEXT DEFAULT NULL)
RETURNS TABLE (tenant_id VARCHAR(36), entries BIGINT, broken_at BIGINT, status TEXT)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_scope TEXT;
    v_entry RECORD;
    v_expected BYTEA;
    v_count BIGINT;
    v_broken BIGINT;
BEGIN
    FOR v_scope IN
        SELECT DISTINCT entry.tenant_id FROM audit_log AS entry
         WHERE p_tenant IS NULL OR entry.tenant_id = p_tenant
         ORDER BY 1
    LOOP
        v_expected := sha256(convert_to('adam-audit-genesis:' || v_scope, 'UTF8'));
        v_count := 0;
        v_broken := NULL;

        FOR v_entry IN
            SELECT * FROM audit_log AS entry
             WHERE entry.tenant_id = v_scope
             ORDER BY entry.id
        LOOP
            v_count := v_count + 1;
            IF v_broken IS NULL AND (
                v_entry.previous_hash IS DISTINCT FROM v_expected
                OR v_entry.entry_hash IS DISTINCT FROM sha256(
                    v_entry.previous_hash || convert_to(fn_audit_payload(
                        v_entry.tenant_id, v_entry.occurred_at, v_entry.transaction_id,
                        v_entry.principal, v_entry.subject, v_entry.session_role,
                        v_entry.operation, v_entry.object_table, v_entry.row_id,
                        v_entry.before_row, v_entry.after_row, v_entry.details), 'UTF8'))
            ) THEN
                v_broken := v_entry.id;
            END IF;
            v_expected := v_entry.entry_hash;
        END LOOP;

        tenant_id := v_scope;
        entries := v_count;
        broken_at := v_broken;
        status := CASE WHEN v_broken IS NULL THEN 'intact' ELSE 'broken' END;
        RETURN NEXT;
    END LOOP;
END;
$$;
