-- 1. Créer l'utilisateur
CREATE USER adam_test WITH PASSWORD 'adam_test';

-- 2. Ajouter les varibles pour DBeaver
ALTER ROLE adam_test SET app.adam.tenant_id TO 'tenantA';
ALTER ROLE adam_test SET app.adam.user_id TO 'adam_test';
ALTER ROLE adam_test SET app.adam.user_attributes TO '{}';

-- 3. Ajout des droits sur les tables
GRANT USAGE ON SCHEMA adam TO adam_test;
GRANT SELECT ON ALL TABLES IN SCHEMA adam TO adam_test;

GRANT INSERT ON relations, roles, permissions TO adam_test;
GRANT INSERT ON relations_attributes, roles_attributes, permissions_attributes TO adam_test;
GRANT INSERT ON model_rules, relations_rules, roles_rules, permissions_rules TO adam_test;

GRANT DELETE ON relations, roles, permissions TO adam_test;
GRANT DELETE ON relations_attributes, roles_attributes, permissions_attributes TO adam_test;
GRANT DELETE ON model_rules, relations_rules, roles_rules, permissions_rules TO adam_test;

-- 4. Ajout des tenants
INSERT INTO tenants_per_users (tenant_id, pg_user) VALUES ('tenantA', 'adam_test');
INSERT INTO tenants_per_users (tenant_id, pg_user) VALUES ('tenantB', 'adam_test');

-- 5. Ajout des droits sur la tables
GRANT USAGE ON SCHEMA contoso TO adam_test;
GRANT SELECT ON ALL TABLES IN SCHEMA contoso TO adam_test;
