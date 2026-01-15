CREATE SCHEMA IF NOT EXISTS qfq;

-- Table Dossier
CREATE TABLE qfq.dossier (
    id VARCHAR(255) PRIMARY KEY,
    nom VARCHAR(100),
    is_confidentiel BOOLEAN,
    siret VARCHAR(14),
    type_entreprise VARCHAR(100),
    code_naf VARCHAR(6),
    tenant VARCHAR(100),
    date_enregistrement TIMESTAMP DEFAULT NOW()
);