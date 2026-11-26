-- 1. Principal authentifié
-- Le sujet OAuth si PostgreSQL a validé un jeton, sinon le rôle courant.
-- system_user vient du serveur, la session ne peut pas le changer.
CREATE OR REPLACE FUNCTION get_authenticated_principal()
RETURNS TEXT
LANGUAGE SQL
STABLE
PARALLEL SAFE
AS $$
    SELECT CASE
        WHEN system_user LIKE 'oauth:%' THEN substring(system_user FROM 7)
        ELSE current_user::text
    END;
$$;

-- 2. Sujet de la requête
-- La variable de session doit correspondre à une délégation enregistrée. Sans
-- aucune délégation, le principal agit sous son propre nom.
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS TEXT AS $$
    SELECT COALESCE(
        (SELECT binding.user_id
           FROM users_per_pg_user AS binding
          WHERE binding.pg_user = get_authenticated_principal()
            AND binding.user_id = current_setting('app.adam.user_id', true)
            AND binding.tenant_id = current_setting('app.adam.tenant_id', true)
          LIMIT 1),
        (SELECT get_authenticated_principal()
          WHERE NOT EXISTS (SELECT 1
                              FROM users_per_pg_user AS binding
                             WHERE binding.pg_user = get_authenticated_principal()))
    );
$$ LANGUAGE SQL STABLE PARALLEL SAFE SECURITY INVOKER;

-- 3. Attributs du sujet
-- Pris dans la liaison. Pas de liaison : objet vide, donc toute contrainte ABAC
-- ou RUBAC échoue.
CREATE OR REPLACE FUNCTION get_current_user_attributes()
RETURNS JSONB AS $$
    SELECT COALESCE(
        (SELECT binding.user_attributes
           FROM users_per_pg_user AS binding
          WHERE binding.pg_user = get_authenticated_principal()
            AND binding.user_id = current_setting('app.adam.user_id', true)
            AND binding.tenant_id = current_setting('app.adam.tenant_id', true)
          LIMIT 1),
        '{}'::jsonb
    );
$$ LANGUAGE SQL STABLE PARALLEL SAFE SECURITY INVOKER;

-- 4. Préfixe de rôle
-- Comparaison littérale : avec LIKE, '_' est un joker et is_allow('delete')
-- acceptait 'deleterevil'.
CREATE OR REPLACE FUNCTION is_allow(prefix TEXT)
RETURNS BOOLEAN AS $$
    SELECT starts_with(CURRENT_USER::text, prefix || '_');
$$ LANGUAGE sql STABLE PARALLEL SAFE;
