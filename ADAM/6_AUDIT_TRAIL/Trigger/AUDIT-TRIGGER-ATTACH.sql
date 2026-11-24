-- 1. Pose du trigger sur toute les tables du schéma
-- Les tables sont énumérées depuis le catalogue, pas listées à la main : une
-- liste nominative s'était déjà révélée incomplète pour le search_path (A01-9).
-- Chaque pose est enregistrée dans audit_coverage, ce qui rend la couverture
-- vérifiable.
DO $$
DECLARE
    v_table TEXT;
BEGIN
    FOR v_table IN
        SELECT c.relname
          FROM pg_class AS c
          JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = current_schema()
           AND c.relkind = 'r'
           AND c.relname NOT IN ('audit_log', 'audit_chain_head', 'audit_coverage')
         ORDER BY c.relname
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_audit_%I ON %I', v_table, v_table);
        EXECUTE format(
            'CREATE TRIGGER trg_audit_%I AFTER INSERT OR UPDATE OR DELETE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION fn_audit_row()', v_table, v_table);
        INSERT INTO audit_coverage(table_name) VALUES (v_table) ON CONFLICT DO NOTHING;
    END LOOP;
END;
$$;
