-- 1. Pour relation_attributes_rules
CREATE TABLE adam.relations_attributes (
    relation_id UUID REFERENCES adam.relations(id) ON DELETE CASCADE,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    attribute JSONB,
    PRIMARY KEY (relation_id, attribute)
);
