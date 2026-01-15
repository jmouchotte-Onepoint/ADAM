-- 1. Pour role_attributes_rules
CREATE TABLE adam.roles_attributes (
    role_id UUID REFERENCES adam.roles(id) ON DELETE CASCADE,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    attribute JSONB,
    PRIMARY KEY (role_id, attribute)
);