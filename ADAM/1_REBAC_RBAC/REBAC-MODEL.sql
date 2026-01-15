-- 1. Creation de l'enum pour le bon format
CREATE TYPE adam.enum_relations_roles_permissions AS ENUM ('RELATIONS', 'ROLES', 'PERMISSIONS');

-- 2. CREATE TABLE FOR RULES PERMISSIONS
CREATE TABLE IF NOT EXISTS adam.model (
    id UUID DEFAULT uuidv7() UNIQUE,
    relation_source_type adam.enum_relations_roles_permissions DEFAULT NULL,
    relation_type adam.enum_relations_roles_permissions NOT NULL,
    relation_source TEXT NOT NULL,
    user_type TEXT NOT NULL,
    relation TEXT NOT NULL,
    object_type TEXT NOT NULL,
    relation_origin TEXT DEFAULT NULL,
    condition TEXT DEFAULT NULL,
    created_date TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_type, relation_source, object_type, relation)
);

-- 3. Lecture
CREATE INDEX idx_model_policy_user_relation ON adam.model (relation, user_type);
CREATE INDEX idx_model_policy_object_relation_source ON adam.model (relation_source, object_type);
CREATE INDEX idx_model_policy_object_relation_user ON adam.model (relation_source, object_type, relation_origin, user_type);

-- 4. Insert dans relations
CREATE INDEX idx_model_policy_fk_relations ON adam.model (user_type, relation_source, object_type, relation);