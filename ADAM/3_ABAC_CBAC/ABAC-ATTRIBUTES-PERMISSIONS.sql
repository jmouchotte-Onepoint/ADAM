-- 1. Pour permission_attributes_rules
CREATE TABLE permissions_attributes (
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    attribute JSONB,
    PRIMARY KEY (permission_id, attribute)
);