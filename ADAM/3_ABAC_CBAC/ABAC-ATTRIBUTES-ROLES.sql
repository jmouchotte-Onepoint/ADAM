-- 1. Pour role_attributes_rules
CREATE TABLE roles_attributes (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    attribute JSONB,
    PRIMARY KEY (role_id, attribute)
);