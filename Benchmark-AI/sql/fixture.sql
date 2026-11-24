CREATE ROLE read_validation LOGIN NOSUPERUSER NOBYPASSRLS;
CREATE SCHEMA parcours;
CREATE TABLE parcours.etapes (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    consent BOOLEAN NOT NULL DEFAULT TRUE,
    value INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE protected_records (LIKE parcours.etapes INCLUDING ALL);
ALTER TABLE protected_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE protected_records FORCE ROW LEVEL SECURITY;

INSERT INTO tenants(id, name) VALUES ('tenantA', 'Validation A'), ('tenantB', 'Validation B');
INSERT INTO tenants_per_users(tenant_id, pg_user) VALUES ('tenantA', 'read_validation');
-- Délégation du rôle PostgreSQL vers le sujet applicatif et ses attributs.
-- Le bloc est conditionnel : le même fixture sert aussi aux installations
-- historiques reconstituées par check_liquibase_migration.py, antérieures à la
-- correction A01.
DO $fixture$
BEGIN
    IF to_regclass('users_per_pg_user') IS NOT NULL THEN
        INSERT INTO users_per_pg_user(pg_user, user_id, tenant_id, user_attributes)
        VALUES ('read_validation', 'nurse', 'tenantA', '{}'::jsonb)
        ON CONFLICT DO NOTHING;
    END IF;
END;
$fixture$;
GRANT USAGE ON SCHEMA adam, parcours TO read_validation;
GRANT SELECT ON ALL TABLES IN SCHEMA adam TO read_validation;
GRANT SELECT, UPDATE, DELETE ON protected_records TO read_validation;
GRANT SELECT ON parcours.etapes TO read_validation;
GRANT INSERT, DELETE ON relations TO read_validation;

INSERT INTO model(relation_type, relation_source, user_type, relation, object_type)
VALUES ('RELATIONS', 'assigned', 'users', 'assigned', 'etapes');
INSERT INTO model(relation_type, relation_source, user_type, relation, object_type)
SELECT 'ROLES', 'assigned', 'users', 'role_' || i, 'etapes'
FROM generate_series(1, 4) i;
INSERT INTO model(relation_type, relation_source, user_type, relation, object_type)
SELECT 'PERMISSIONS', 'assigned', 'users',
       CASE i WHEN 1 THEN 'can_read' WHEN 2 THEN 'can_write' ELSE 'permission_' || i END,
       'etapes'
FROM generate_series(1, 21) i;

-- Experimental adapter, not a replacement for the repository-generated policy.
CREATE POLICY validation_select ON protected_records FOR SELECT TO read_validation USING (
    tenant_id = get_current_tenant_id()
    AND consent
    AND EXISTS (
        SELECT 1 FROM permissions p
        JOIN relations source ON source.id = p.parent_relation_id
        WHERE p.user_type = 'users'
          AND p.user_id = get_current_user_id()
          AND p.object_type = 'etapes'
          AND p.object_id = protected_records.id
          AND p.tenant_id = protected_records.tenant_id
          AND p.relation = 'can_read'
          AND p.allow_deny IS TRUE AND source.allow_deny IS TRUE
          AND (p.expires_at IS NULL OR p.expires_at > statement_timestamp())
          AND (source.expires_at IS NULL OR source.expires_at > statement_timestamp())
          AND NOT EXISTS (
              SELECT 1 FROM view_all_access_attributes a
              WHERE a.id = p.id AND a.relation_type = 'permissions'
                AND fn_check_attributes(get_current_user_attributes(), a.attribute) IS NOT TRUE
          )
          AND fn_check_all_rules_from_view(p.id, 'permissions', get_current_user_attributes()) IS TRUE
    )
);
CREATE POLICY validation_update ON protected_records FOR UPDATE TO read_validation
USING (
    tenant_id = get_current_tenant_id() AND consent
    AND EXISTS (
        SELECT 1 FROM permissions p JOIN relations source ON source.id = p.parent_relation_id
        WHERE p.user_id = get_current_user_id() AND p.user_type = 'users'
          AND p.object_id = protected_records.id AND p.object_type = 'etapes'
          AND p.tenant_id = protected_records.tenant_id AND p.relation = 'can_write'
          AND p.allow_deny IS TRUE AND source.allow_deny IS TRUE
          AND (source.expires_at IS NULL OR source.expires_at > statement_timestamp())
          AND (p.expires_at IS NULL OR p.expires_at > statement_timestamp())
          AND NOT EXISTS (
              SELECT 1 FROM view_all_access_attributes a
              WHERE a.id = p.id AND a.relation_type = 'permissions'
                AND fn_check_attributes(get_current_user_attributes(), a.attribute) IS NOT TRUE
          )
          AND fn_check_all_rules_from_view(p.id, 'permissions', get_current_user_attributes()) IS TRUE
    )
) WITH CHECK (tenant_id = get_current_tenant_id() AND consent);
