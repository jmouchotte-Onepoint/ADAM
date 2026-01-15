-- 1. Création de la table pour des règles SQL
CREATE TABLE IF NOT EXISTS adam.dynamic_rules(
    id UUID DEFAULT uuidv7(),
    rule TEXT NOT NULL,
    params TEXT[] NULL,
    description TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id)
);