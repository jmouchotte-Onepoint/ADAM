-- 1. Créer l'utilisateur
CREATE USER adam_test WITH PASSWORD 'adam_test';

-- 2. Ajouter les varibles pour DBeaver
ALTER ROLE adam_test SET app.adam.tenant_id TO 'tenant_01';
ALTER ROLE adam_test SET app.adam.user_id TO 'adam_test';
ALTER ROLE adam_test SET app.adam.user_attributes TO '{}';

-- 3. Ajout des droits sur les tables
GRANT USAGE ON SCHEMA adam TO adam_test;
GRANT SELECT ON ALL TABLES IN SCHEMA adam TO adam_test;

GRANT INSERT ON adam.relations, adam.roles, adam.permissions TO adam_test;
GRANT INSERT ON adam.relations_attributes, adam.roles_attributes, adam.permissions_attributes TO adam_test;
GRANT INSERT ON adam.model_rules, adam.relations_rules, adam.roles_rules, adam.permissions_rules TO adam_test;

GRANT DELETE ON adam.relations, adam.roles, adam.permissions TO adam_test;
GRANT DELETE ON adam.relations_attributes, adam.roles_attributes, adam.permissions_attributes TO adam_test;
GRANT DELETE ON adam.model_rules, adam.relations_rules, adam.roles_rules, adam.permissions_rules TO adam_test;

-- 4. Ajout des tenants
INSERT INTO adam.tenants_per_users (tenant_id, pg_user) VALUES ('tenant_01', 'adam_test');
INSERT INTO adam.tenants_per_users (tenant_id, pg_user) VALUES ('tenant_02', 'adam_test');