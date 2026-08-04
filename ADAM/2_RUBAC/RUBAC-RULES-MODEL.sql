-- 1. Création de la table pour des règles SQL
CREATE TABLE IF NOT EXISTS model_rules(
    model_id UUID REFERENCES model(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES dynamic_rules(id) ON DELETE CASCADE,
    params JSONB DEFAULT NULL::jsonb,
    PRIMARY KEY (model_id, rule_id)
);