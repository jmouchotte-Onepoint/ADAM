-- 1. Initialisation pour set up la récursivitée
CREATE OR REPLACE FUNCTION fn_insert_roles_permissions_from_roles() 
RETURNS TRIGGER AS $$
BEGIN
    -- Appel de la fonction helper avec PERFORM
    PERFORM fn_recursive_insert_roles_permissions(
        NEW.deep,
        NEW.id,
        NEW.user_type,
        NEW.user_id,
        NEW.relation,
        'ROLES',
        NEW.object_type,
        NEW.object_id,
        NEW.tenant_id,
        NEW.model_id,
        NEW.id,
        NEW.parent_relation_id,
        NEW.ancestor_relation_id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Créer le trigger recursif
DROP TRIGGER IF EXISTS trg_roles_after_insert_01_roles_permissions ON roles;

CREATE TRIGGER trg_roles_after_insert_01_roles_permissions
AFTER INSERT ON roles
FOR EACH ROW
WHEN (NEW.is_auto_generated = FALSE)
EXECUTE FUNCTION fn_insert_roles_permissions_from_roles();

-- 3. Créer le trigger pour set tup
DROP TRIGGER IF EXISTS trg_roles_before_insert_01_set_model_id ON roles;

CREATE TRIGGER trg_roles_before_insert_01_set_model_id
BEFORE INSERT OR UPDATE ON roles
FOR EACH ROW
EXECUTE FUNCTION fn_trigger_set_model_id();

-- 4. Créer le trigger pour auto-peupler condition_relation_id sur roles
DROP TRIGGER IF EXISTS trg_roles_before_insert_02_set_condition_relation_id ON roles;

CREATE TRIGGER trg_roles_before_insert_02_set_condition_relation_id
BEFORE INSERT ON roles
FOR EACH ROW
EXECUTE FUNCTION fn_trigger_set_relations_condition_relation_id();

-- 5. Créer le trigger pour auto-peupler condition_relation_id sur permissions
DROP TRIGGER IF EXISTS trg_permissions_before_insert_01_set_condition_relation_id ON permissions;

CREATE TRIGGER trg_permissions_before_insert_01_set_condition_relation_id
BEFORE INSERT ON permissions
FOR EACH ROW
EXECUTE FUNCTION fn_trigger_set_relations_condition_relation_id();