-- 1. Contenu canonique d'une entrée
-- Même expression à l'écriture et à la vérification. L'horodatage est forcé en
-- UTC : le rendu par défaut d'un timestamptz dépend des réglages de session.
CREATE OR REPLACE FUNCTION fn_audit_payload(
    p_tenant TEXT, p_occurred TIMESTAMPTZ, p_transaction BIGINT, p_principal TEXT,
    p_subject TEXT, p_session_role TEXT, p_operation TEXT, p_table TEXT,
    p_row_id TEXT, p_before JSONB, p_after JSONB, p_details JSONB
)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT concat_ws('|',
        p_tenant,
        to_char(p_occurred AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'),
        p_transaction::text, p_principal, COALESCE(p_subject, ''), p_session_role,
        p_operation, p_table, COALESCE(p_row_id, ''),
        COALESCE(p_before::text, ''), COALESCE(p_after::text, ''),
        COALESCE(p_details::text, ''));
$$;
