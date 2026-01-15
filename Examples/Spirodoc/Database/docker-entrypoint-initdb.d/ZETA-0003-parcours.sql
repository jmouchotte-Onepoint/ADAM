CREATE SCHEMA IF NOT EXISTS parcours;

-- Table Description
CREATE TABLE parcours.infos (
    id VARCHAR(255) PRIMARY KEY,
    nom VARCHAR(100),
    patient_id VARCHAR(255) REFERENCES utilisateur.patients(id),
    pathologie VARCHAR(255),
    date_creation DATE,
    date_fin DATE,
    observation TEXT,
    date_enregistrement TIMESTAMP DEFAULT NOW()
);

-- Table Referent Parcours
CREATE TABLE parcours.referents (
    parcours_id VARCHAR(255) REFERENCES parcours.infos(id),
    referent_id VARCHAR(255) REFERENCES utilisateur.effecteurs(id),
    date_enregistrement TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (parcours_id, referent_id)
);

-- Table Etape
CREATE TABLE parcours.etapes (
    id VARCHAR(255) PRIMARY KEY,
    parcours_id VARCHAR(255) REFERENCES parcours.infos(id),
    nom VARCHAR(100),
    date_creation DATE,
    date_fin DATE,
    observation TEXT,
    date_enregistrement TIMESTAMP DEFAULT NOW()
);

-- Table Invités (effecteurs participant à un parcours)
CREATE TABLE parcours.invites (
    etape_id VARCHAR(255) REFERENCES parcours.etapes(id),
    invite_id VARCHAR(255) REFERENCES utilisateur.effecteurs(id),
    date_enregistrement TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (etape_id, invite_id)
);