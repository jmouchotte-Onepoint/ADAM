-- === Schéma utilisateur ===

CREATE SCHEMA IF NOT EXISTS utilisateur;

CREATE TABLE utilisateur.users (
    id VARCHAR(255) PRIMARY KEY,
    nom VARCHAR(100),
    prenom VARCHAR(100),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    date_enregistrement TIMESTAMP DEFAULT NOW()
);