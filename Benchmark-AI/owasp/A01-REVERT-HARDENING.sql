-- Retour aux définitions publiées, avant les corrections OWASP A01.
--
-- Les correctifs sont désormais dans les fichiers de référence des couches 0 à
-- 3 : on ne peut plus construire la base « avant correction » en retirant un
-- changeset. Ce fichier restaure donc les définitions d'origine sur une
-- installation à jour. Tout le reste est identique entre les deux variantes,
-- journal d'audit compris : la seule variable est le durcissement.
--
-- Si ce retour arrière est incomplet, une sonde cessera d'aboutir sur la base de
-- référence et check_owasp_a01.py échouera : la complétude est donc vérifiée par
-- l'audit lui-même.

-- A01-1 / A01-2 / A01-3 : l'identité redevient déclarative
CREATE OR REPLACE FUNCTION get_current_user_attributes()
RETURNS JSONB AS $$
    SELECT current_setting('app.adam.user_attributes', true)::jsonb;
$$ LANGUAGE SQL STABLE SECURITY INVOKER;

CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS TEXT AS $$
    SELECT current_setting('app.adam.user_id',true)
$$ LANGUAGE SQL STABLE SECURITY INVOKER;

-- La table de délégation reste en place : ce qui est restauré, c'est le
-- comportement publié des accesseurs, qui l'ignorent. La supprimer casserait
-- le journal d'audit, qui la lit, et ferait varier deux choses à la fois.
ALTER TABLE tenants_per_users DISABLE ROW LEVEL SECURITY;

-- A01-6 : le préfixe de rôle repasse en LIKE
CREATE OR REPLACE FUNCTION is_allow(prefix TEXT)
RETURNS BOOLEAN AS $$
    SELECT CURRENT_USER LIKE prefix || '_%';
$$ LANGUAGE sql STABLE PARALLEL SAFE;

-- A01-7 : métadonnées sans portée de tenant, vues avec les droits du propriétaire
DO $$
DECLARE
    v_table TEXT;
    v_column TEXT;
BEGIN
    FOREACH v_table IN ARRAY ARRAY['relations_attributes', 'roles_attributes',
                                   'permissions_attributes', 'relations_rules',
                                   'roles_rules', 'permissions_rules']
    LOOP
        v_column := CASE
            WHEN v_table LIKE 'relations%' THEN 'relation_id'
            WHEN v_table LIKE 'roles%' THEN 'role_id'
            ELSE 'permission_id'
        END;
        EXECUTE format('DROP POLICY IF EXISTS policy_select_%s ON %I', v_table, v_table);
        EXECUTE format(
            'CREATE POLICY policy_select_%s ON %I FOR SELECT '
            'USING (%I IS NOT NULL AND get_current_user_id() IS NOT NULL)',
            v_table, v_table, v_column);
    END LOOP;
END;
$$;

ALTER VIEW view_relations_attributes SET (security_invoker = false);
ALTER VIEW view_roles_attributes SET (security_invoker = false);
ALTER VIEW view_permissions_attributes SET (security_invoker = false);
ALTER VIEW view_all_access_attributes SET (security_invoker = false);
ALTER VIEW view_relations_rules SET (security_invoker = false);
ALTER VIEW view_roles_rules SET (security_invoker = false);
ALTER VIEW view_permissions_rules SET (security_invoker = false);
ALTER VIEW view_all_access_rules SET (security_invoker = false);

ALTER FUNCTION fn_check_all_attributes_from_view(uuid, text, jsonb) SECURITY DEFINER;
ALTER FUNCTION fn_check_all_rules_from_view(uuid, text, jsonb) SECURITY DEFINER;

-- A01-5 : dynamic_rules sans RLS
ALTER TABLE dynamic_rules DISABLE ROW LEVEL SECURITY;

-- A01-8 : l'invariant n'est plus vérifiable
DROP FUNCTION IF EXISTS fn_check_runtime_role(TEXT);

-- A01-4 / A01-5 / A01-9 : search_path de nouveau ouvert à pg_temp
DO $$
DECLARE
    v_function RECORD;
BEGIN
    FOR v_function IN
        SELECT p.oid::regprocedure AS signature
          FROM pg_proc AS p
          JOIN pg_namespace AS n ON n.oid = p.pronamespace
         WHERE n.nspname = current_schema()
           AND p.prokind = 'f'
    LOOP
        EXECUTE format('ALTER FUNCTION %s RESET search_path', v_function.signature);
    END LOOP;
END;
$$;
