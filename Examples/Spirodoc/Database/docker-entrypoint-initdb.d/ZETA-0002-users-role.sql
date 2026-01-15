-- === Schéma utilisateur ===

-- Table Adresse Utilisateur
CREATE TABLE utilisateur.adresses (
    id VARCHAR(255) PRIMARY KEY,
    adresse VARCHAR(255),
    complement_adresse VARCHAR(255),
    ville VARCHAR(255),
    code_postal VARCHAR(255),
    pays VARCHAR(255)
);

-- Table Patient
CREATE TABLE utilisateur.patients (
    id VARCHAR(255) PRIMARY KEY REFERENCES utilisateur.users(id),
    adresse VARCHAR(255) REFERENCES utilisateur.adresses(id),
    age INT,
    sexe VARCHAR(10),
    profession VARCHAR(100),
    date_naissance VARCHAR(10),
    numero_telephone VARCHAR(15),
    numero_securite_social VARCHAR(255),
    date_enregistrement TIMESTAMP DEFAULT NOW()
);

-- Table Effecteur (Médecins, Infirmiers, etc.)
CREATE TABLE utilisateur.effecteurs (
    id VARCHAR(255) PRIMARY KEY REFERENCES utilisateur.users(id),
    adresse_professionnel VARCHAR(255) REFERENCES utilisateur.adresses(id),
    numero_professionnel VARCHAR(255),
    specialite VARCHAR(50),
    date_enregistrement TIMESTAMP DEFAULT NOW()
);
