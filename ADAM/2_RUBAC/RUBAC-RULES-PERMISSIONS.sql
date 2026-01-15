-- 1. Création de la table pour des règles SQL
CREATE TABLE IF NOT EXISTS adam.permissions_rules(
    permission_id UUID REFERENCES adam.permissions(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES adam.dynamic_rules(id) ON DELETE CASCADE,
    params JSONB DEFAULT NULL::jsonb,
    is_inheritable BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (permission_id, rule_id)
);