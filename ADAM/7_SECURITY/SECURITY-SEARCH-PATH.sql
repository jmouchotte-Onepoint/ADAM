-- 1. search_path figé sur toutes les fonctions du schéma
-- PostgreSQL consulte pg_temp en premier tant qu'il n'est pas listé : un objet
-- temporaire du même nom qu'une table ou une vue lue par une fonction la
-- remplace. C'est le cas des règles à l'évaluation (A01-4/5) comme de `model` à
-- la dérivation (A01-9). Les fonctions sont énumérées depuis le catalogue : une
-- liste écrite à la main s'était révélée incomplète.
--
-- Cette couche passe en dernier pour voir toutes les fonctions, y compris
-- celles du journal d'audit.
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
        EXECUTE format('ALTER FUNCTION %s SET search_path = pg_catalog, %I, pg_temp',
                       v_function.signature, current_schema());
    END LOOP;
END;
$$;
