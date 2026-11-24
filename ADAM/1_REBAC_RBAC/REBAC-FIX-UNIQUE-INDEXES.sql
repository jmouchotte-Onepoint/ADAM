-- Correctif pour les bases installées avant l'ajout de NULLS NOT DISTINCT.
-- Les définitions de référence sont dans 1_REBAC_RBAC/REBAC-ROLES.sql et
-- REBAC-PERMISSIONS.sql : une installation neuve a déjà le bon index, on ne le
-- recrée donc que s'il est encore dans son ancienne forme.
DO $$
DECLARE
    v_index TEXT;
    v_table TEXT;
BEGIN
    FOREACH v_index IN ARRAY ARRAY['idx_uniq_roles', 'idx_uniq_permissions']
    LOOP
        v_table := CASE v_index WHEN 'idx_uniq_roles' THEN 'roles' ELSE 'permissions' END;

        CONTINUE WHEN EXISTS (
            SELECT 1
              FROM pg_index AS i
              JOIN pg_class AS c ON c.oid = i.indexrelid
              JOIN pg_namespace AS n ON n.oid = c.relnamespace
             WHERE n.nspname = current_schema()
               AND c.relname = v_index
               AND i.indnullsnotdistinct
        );

        EXECUTE format('DROP INDEX IF EXISTS %I', v_index);
        EXECUTE format(
            'CREATE UNIQUE INDEX %I ON %I '
            '(user_id, relation, object_id, tenant_id, parent_role_id, parent_relation_id) '
            'NULLS NOT DISTINCT', v_index, v_table);
    END LOOP;
END;
$$;
