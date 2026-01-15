-- 1. Initialisation pour set up la récursivitée
CREATE OR REPLACE FUNCTION adam.fn_insert_roles_permissions_from_relation() 
RETURNS TRIGGER AS $$
BEGIN
    -- Appel de la fonction helper avec PERFORM
    PERFORM adam.fn_recursive_insert_roles_permissions(
        NEW.deep,
        NEW.id,
        NEW.user_type,
        NEW.user_id,
        NEW.relation,
        'RELATIONS',
        NEW.object_type,
        NEW.object_id,
        NEW.tenant_id,
        NEW.model_id,
        NULL,        -- parent_role_id
        NEW.id,      -- parent_relation_id
        NULL         -- ancestor_relation_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Créer le trigger recursif
DROP TRIGGER IF EXISTS trg_relations_after_insert_01_roles_permissions ON adam.relations;

CREATE TRIGGER trg_relations_after_insert_01_roles_permissions
AFTER INSERT ON adam.relations
FOR EACH ROW
WHEN (NEW.is_auto_generated = FALSE)
EXECUTE FUNCTION adam.fn_insert_roles_permissions_from_relation();

-- 3. Créer le trigger pour set tup
DROP TRIGGER IF EXISTS trg_relations_before_insert_01_set_model_id ON adam.relations;

CREATE TRIGGER trg_relations_before_insert_01_set_model_id
BEFORE INSERT OR UPDATE ON adam.relations
FOR EACH ROW
EXECUTE FUNCTION adam.fn_trigger_set_model_id();