-- 1. Invariant de déploiement du rôle applicatif
-- La RLS ne s'applique pas au propriétaire d'une table, et FORCE ROW LEVEL
-- SECURITY n'y change rien puisqu'il peut la retirer. Le contrôle est donc un
-- invariant à vérifier depuis le catalogue : une ligne par violation, aucune
-- ligne pour un rôle conforme.
CREATE OR REPLACE FUNCTION fn_check_runtime_role(p_role TEXT)
RETURNS TABLE (violation TEXT, detail TEXT)
LANGUAGE SQL
STABLE
AS $$
    SELECT 'unknown_role', p_role
    WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = p_role)

    UNION ALL
    SELECT 'superuser', p_role
    FROM pg_roles WHERE rolname = p_role AND rolsuper

    UNION ALL
    SELECT 'bypassrls', p_role
    FROM pg_roles WHERE rolname = p_role AND rolbypassrls

    UNION ALL
    SELECT 'member_of_privileged_role', privileged.rolname
    FROM pg_roles AS runtime
    JOIN pg_roles AS privileged
      ON (privileged.rolsuper OR privileged.rolbypassrls)
     AND privileged.rolname <> runtime.rolname
     AND pg_has_role(runtime.oid, privileged.oid, 'MEMBER')
    WHERE runtime.rolname = p_role

    UNION ALL
    SELECT 'owns_rls_table', protected.relname::text
    FROM pg_roles AS runtime
    JOIN pg_class AS protected
      ON protected.relkind IN ('r', 'p')
     AND protected.relrowsecurity
     AND pg_has_role(runtime.oid, protected.relowner, 'MEMBER')
    JOIN pg_namespace AS schema_of ON schema_of.oid = protected.relnamespace
    WHERE runtime.rolname = p_role
      AND schema_of.nspname <> 'information_schema'
      AND left(schema_of.nspname, 3) <> 'pg_';
$$;
