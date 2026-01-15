-- 1. Créer l'utilisateur
CREATE USER read_only_tenant_01 WITH PASSWORD 'read_only_tenant_01';
CREATE USER read_only_tenant_02 WITH PASSWORD 'read_only_tenant_02';

-- 2. Ajouter les variables pour DBeaver
ALTER ROLE read_only_tenant_01 SET app.adam.tenant_id TO 'tenant_01';
ALTER ROLE read_only_tenant_02 SET app.adam.tenant_id TO 'tenant_02';

-- 3. Ajout des droits sur les tables
GRANT USAGE ON SCHEMA adam TO read_only_tenant_01, read_only_tenant_02;
GRANT SELECT ON ALL TABLES IN SCHEMA adam TO read_only_tenant_01, read_only_tenant_02;

GRANT USAGE ON SCHEMA parcours TO adam_test,read_only_tenant_01, read_only_tenant_02;
GRANT SELECT ON ALL TABLES IN SCHEMA sante TO adam_test,read_only_tenant_01, read_only_tenant_02;
GRANT SELECT ON ALL TABLES IN SCHEMA parcours TO adam_test,read_only_tenant_01, read_only_tenant_02;
GRANT SELECT ON ALL TABLES IN SCHEMA utilisateur TO adam_test,read_only_tenant_01, read_only_tenant_02;

-- 4. Ajout des tenants
INSERT INTO adam.tenants_per_users (tenant_id, pg_user) VALUES ('tenant_01', 'read_only_tenant_01');
INSERT INTO adam.tenants_per_users (tenant_id, pg_user) VALUES ('tenant_02', 'read_only_tenant_02');
