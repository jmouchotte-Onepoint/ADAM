-- 1. CREATE TABLE RELATIONS
CREATE TABLE IF NOT EXISTS relations(
    id UUID DEFAULT uuidv7() UNIQUE,
    deep INT DEFAULT 0,
    user_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
    allow_deny BOOLEAN DEFAULT true,
    model_id UUID NOT NULL,
    condition_relation_id UUID DEFAULT NULL,
    is_auto_generated BOOLEAN DEFAULT false,
    created_by TEXT NOT NULL DEFAULT get_current_user_id(),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_type, user_id, relation, object_type, object_id, tenant_id),
    -- Clé étrangère vers les règles valides
    FOREIGN KEY (model_id) REFERENCES model(id) ON DELETE RESTRICT,
    FOREIGN KEY (condition_relation_id) REFERENCES relations(id) ON DELETE CASCADE
);

-- 2. Index pour les suppressions en cascades

-- 3. Index pour insertions
CREATE INDEX idx_relations_user_tenant ON relations (user_type, user_id, tenant_id);
CREATE INDEX idx_relations_tenant ON relations (object_type, object_id, tenant_id);

-- 4. Index pour lecture
CREATE INDEX idx_relations_user_object_tenant ON relations(user_type, object_type, user_id, object_id, tenant_id);