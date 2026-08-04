-- 1. Pour relation_attributes_rules
CREATE TABLE relations_attributes (
    relation_id UUID REFERENCES relations(id) ON DELETE CASCADE,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    attribute JSONB,
    PRIMARY KEY (relation_id, attribute)
);
