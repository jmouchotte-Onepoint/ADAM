-- 1. Créer le trigger pour check
DROP TRIGGER IF EXISTS trg_relations_before_insert_02_check_model_rules ON adam.relations;

CREATE TRIGGER trg_relations_before_insert_02_check_model_rules
BEFORE INSERT OR UPDATE ON adam.relations
FOR EACH ROW
EXECUTE FUNCTION adam.fn_trigger_check_rules_from_model();