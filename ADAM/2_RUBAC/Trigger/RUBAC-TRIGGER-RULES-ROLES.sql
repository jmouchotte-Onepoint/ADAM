-- 1. Créer le trigger pour check
DROP TRIGGER IF EXISTS trg_roles_before_insert_02_check_model_rules ON roles;

CREATE TRIGGER trg_roles_before_insert_02_check_model_rules
BEFORE INSERT OR UPDATE ON roles
FOR EACH ROW
EXECUTE FUNCTION fn_trigger_check_rules_from_model();