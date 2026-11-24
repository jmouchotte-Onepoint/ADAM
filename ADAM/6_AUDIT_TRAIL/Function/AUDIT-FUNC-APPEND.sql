-- 1. Ajout d'une entrée
-- Retirée de PUBLIC : seules les fonctions de ce dossier l'appellent.
-- Dans une fonction SECURITY DEFINER, current_user vaut le propriétaire. On
-- s'appuie donc sur system_user et session_user, posés par le serveur et
-- insensibles à SET ROLE.
-- Le verrou sur la tête de chaîne sérialise les écritures d'un même tenant :
-- c'est le prix d'une chaîne sans fourche. Une transaction qui touche à la fois
-- un tenant et la chaîne globale prend deux verrous, donc deux transactions en
-- sens inverse peuvent se bloquer et PostgreSQL en annule une.
CREATE OR REPLACE FUNCTION fn_audit_append(
    p_tenant TEXT, p_operation TEXT, p_table TEXT, p_row_id TEXT,
    p_before JSONB, p_after JSONB, p_details JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_tenant VARCHAR(36) := COALESCE(NULLIF(p_tenant, ''), '*');
    v_principal TEXT;
    v_subject TEXT;
    v_occurred TIMESTAMPTZ := clock_timestamp();
    v_transaction BIGINT := pg_current_xact_id()::text::bigint;
    v_previous BYTEA;
    v_hash BYTEA;
    v_id BIGINT;
BEGIN
    v_principal := CASE
        WHEN system_user LIKE 'oauth:%' THEN substring(system_user FROM 7)
        ELSE session_user::text
    END;

    -- Le sujet n'est retenu que s'il correspond à une délégation enregistrée.
    SELECT binding.user_id INTO v_subject
      FROM users_per_pg_user AS binding
     WHERE binding.pg_user = v_principal
       AND binding.user_id = current_setting('app.adam.user_id', true)
       AND binding.tenant_id = current_setting('app.adam.tenant_id', true)
     LIMIT 1;

    IF v_subject IS NULL AND NOT EXISTS (
        SELECT 1 FROM users_per_pg_user AS binding WHERE binding.pg_user = v_principal
    ) THEN
        v_subject := v_principal;
    END IF;

    -- La tête existe dès la deuxième écriture du tenant : on la lit d'abord et
    -- on ne tente la création que si elle manque, plutôt qu'un INSERT en
    -- conflit à chaque ligne auditée.
    SELECT last_hash INTO v_previous
      FROM audit_chain_head
     WHERE tenant_id = v_tenant
       FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO audit_chain_head(tenant_id, last_hash)
        VALUES (v_tenant, sha256(convert_to('adam-audit-genesis:' || v_tenant, 'UTF8')))
        ON CONFLICT (tenant_id) DO NOTHING;

        SELECT last_hash INTO v_previous
          FROM audit_chain_head
         WHERE tenant_id = v_tenant
           FOR UPDATE;
    END IF;

    v_hash := sha256(v_previous || convert_to(fn_audit_payload(
        v_tenant, v_occurred, v_transaction, v_principal, v_subject, session_user::text,
        p_operation, p_table, p_row_id, p_before, p_after, p_details), 'UTF8'));

    INSERT INTO audit_log(tenant_id, occurred_at, transaction_id, principal, subject,
                          session_role, operation, object_table, row_id, before_row,
                          after_row, details, previous_hash, entry_hash)
    VALUES (v_tenant, v_occurred, v_transaction, v_principal, v_subject,
            session_user::text, p_operation, p_table, p_row_id, p_before,
            p_after, p_details, v_previous, v_hash)
    RETURNING id INTO v_id;

    UPDATE audit_chain_head
       SET last_hash = v_hash, entries = entries + 1, updated_at = v_occurred
     WHERE tenant_id = v_tenant;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION fn_audit_append(TEXT, TEXT, TEXT, TEXT, JSONB, JSONB, JSONB) FROM PUBLIC;
