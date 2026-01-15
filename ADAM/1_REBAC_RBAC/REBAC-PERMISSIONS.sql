-- 1. CREATE TABLE PERMISSIONS
CREATE TABLE IF NOT EXISTS adam.permissions (
    id UUID DEFAULT uuidv7() PRIMARY KEY,
    deep INT DEFAULT 0,
    user_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    tenant_id VARCHAR(36) NOT NULL REFERENCES adam.tenants(id),
    allow_deny BOOLEAN DEFAULT true,
    model_id UUID NOT NULL,
    parent_role_id UUID DEFAULT NULL,
    parent_relation_id UUID DEFAULT NULL,
    ancestor_relation_id UUID DEFAULT NULL,
    is_auto_generated BOOLEAN DEFAULT false,
    created_by TEXT NOT NULL DEFAULT adam.get_current_user_id(),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (model_id) REFERENCES adam.model(id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_role_id) REFERENCES adam.roles(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_relation_id) REFERENCES adam.relations(id) ON DELETE CASCADE,
    FOREIGN KEY (ancestor_relation_id) REFERENCES adam.relations(id) ON DELETE SET NULL
);

-- 2. Index pour les suppressions en cascades
CREATE INDEX idx_permissions_parent_role_id ON adam.permissions (parent_role_id);
CREATE INDEX idx_permissions_parent_relation_id ON adam.permissions (parent_relation_id);

-- 3. Index pour insertions
CREATE UNIQUE INDEX idx_uniq_permissions ON adam.permissions (user_id,relation,object_id,tenant_id,COALESCE(parent_role_id, '00000000-0000-0000-0000-000000000000'::uuid),parent_relation_id);

-- 4. Index pour lecture
CREATE INDEX idx_permissions_user_object_tenant ON adam.roles(user_type, user_id, relation, object_type, object_id, tenant_id);
