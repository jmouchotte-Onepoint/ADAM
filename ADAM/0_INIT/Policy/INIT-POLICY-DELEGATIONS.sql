-- 1. Un rôle ne voit que ses propres délégations
DROP POLICY IF EXISTS policy_select_users_per_pg_user ON users_per_pg_user;
CREATE POLICY policy_select_users_per_pg_user
    ON users_per_pg_user
    FOR SELECT
    USING (pg_user = get_authenticated_principal());

DROP POLICY IF EXISTS policy_select_tenants_per_users ON tenants_per_users;
CREATE POLICY policy_select_tenants_per_users
    ON tenants_per_users
    FOR SELECT
    USING (pg_user = current_user);

-- 2. Pas de politique d'écriture : les liaisons restent au propriétaire du schéma.
