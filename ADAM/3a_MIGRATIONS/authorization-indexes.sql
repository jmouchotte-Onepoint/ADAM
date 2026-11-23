DROP INDEX idx_uniq_roles;
CREATE UNIQUE INDEX idx_uniq_roles
    ON roles (user_id, relation, object_id, tenant_id, parent_role_id, parent_relation_id) NULLS NOT DISTINCT;

DROP INDEX idx_uniq_permissions;
CREATE UNIQUE INDEX idx_uniq_permissions
    ON permissions (user_id, relation, object_id, tenant_id, parent_role_id, parent_relation_id) NULLS NOT DISTINCT;
