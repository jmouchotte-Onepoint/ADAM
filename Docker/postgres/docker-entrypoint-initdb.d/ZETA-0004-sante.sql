-- === Schéma sante (documents) ===
CREATE SCHEMA IF NOT EXISTS sante;

CREATE TABLE sante.containers (
    id VARCHAR(255) PRIMARY KEY,
    parcours_id VARCHAR(255) NOT NULL REFERENCES parcours.infos(id),
    utlisateur_id VARCHAR(255) NOT NULL REFERENCES utilisateur.users(id),
    nom VARCHAR(255),
    date_enregistrement TIMESTAMP DEFAULT NOW(),
    actif BOOLEAN DEFAULT TRUE
);

CREATE TABLE sante.objets (
    id VARCHAR(255) PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    date_creation TIMESTAMP DEFAULT NOW(),
    date_suppression TIMESTAMP,
    container_id VARCHAR(255) NOT NULL REFERENCES sante.containers(id),
    user_id VARCHAR(255) NOT NULL REFERENCES utilisateur.users(id),
    empreinte VARCHAR(255),
    supprime BOOLEAN DEFAULT FALSE
);

-- Table FicheEntity Generique
CREATE TABLE sante.fiches (
    id VARCHAR(255) PRIMARY KEY,
    etape_id VARCHAR(255) REFERENCES parcours.etapes(id),
    patient_id VARCHAR(255) REFERENCES utilisateur.patients(id),
    document_id VARCHAR(255) REFERENCES sante.objets(id),
    type VARCHAR(255),
    nom VARCHAR(255),
    observation TEXT,
    resultats JSONB,
    date_creation DATE,
    date_suppression DATE,
    date_enregistrement TIMESTAMP DEFAULT NOW()
);