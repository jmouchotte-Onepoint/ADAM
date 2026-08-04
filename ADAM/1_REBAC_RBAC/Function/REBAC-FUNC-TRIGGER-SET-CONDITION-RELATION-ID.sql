-- 1. Fonction trigger pour auto-peupler condition_relation_id
CREATE OR REPLACE FUNCTION fn_trigger_set_relations_condition_relation_id()
RETURNS TRIGGER AS $$
DECLARE
    v_condition_relation_id UUID;
    v_relation_type enum_relations_roles_permissions;
BEGIN
    IF TG_TABLE_NAME = 'relations' THEN
        v_relation_type := 'RELATIONS';
    ELSIF TG_TABLE_NAME = 'roles' THEN
        v_relation_type := 'ROLES';
    ELSIF TG_TABLE_NAME = 'permissions' THEN
        v_relation_type := 'PERMISSIONS';
    ELSE
        RAISE EXCEPTION '[P30002] Table non supportee pour fn_trigger_set_relations_condition_relation_id: %', TG_TABLE_NAME;
    END IF;

    -- La fonction leve deja une exception si une condition est requise mais non satisfaite.
    v_condition_relation_id := fn_check_model_condition(
        v_relation_type,
        NEW.user_type,
        NEW.user_id,
        NEW.relation,
        NEW.object_type,
        NEW.object_id,
        NEW.model_id
    );

    -- Si aucune condition n'est requise, on conserve NULL en base.
    IF v_condition_relation_id = '00000000-0000-0000-0000-000000000000'::UUID THEN
        NEW.condition_relation_id := NULL;
    ELSE
        NEW.condition_relation_id := v_condition_relation_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;