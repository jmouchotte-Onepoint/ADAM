--- Initialisation ---
ALTER TABLE parcours.etapes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS adam_policy_select_parcours_etapes ON parcours.etapes;

CREATE POLICY adam_policy_select_parcours_etapes ON parcours.etapes
    FOR SELECT
    USING (
		EXISTS (
            SELECT 1 FROM permissions AS rrp
            WHERE rrp.relation = 'can_read'
            AND rrp.object_type = 'etapes'
            AND rrp.allow_deny IS TRUE
            AND rrp.user_id = get_current_user_id()
            AND rrp.tenant_id = get_current_tenant_id()
            AND (rrp.expires_at IS NULL OR rrp.expires_at > statement_timestamp())
			AND parcours.etapes.id like 'parcours-%'
			AND parcours.etapes.id = rrp.object_id
		)
); 

