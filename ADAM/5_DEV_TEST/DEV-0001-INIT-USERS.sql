-- UTILISATEUR : users
INSERT INTO utilisateur.users (id, username, nom, prenom, email) VALUES
    ('patient-1', 'jdurand', 'Durand', 'Jean', 'jdurand@example.com'),
    ('patient-2', 'mleclerc', 'Leclerc', 'Marie', 'mleclerc@example.com'),
    ('effecteur-med-1', 'tlaporte', 'Laporte', 'Thomas', 'tlaporte@example.com'),
    ('effecteur-inf-1', 'acollet', 'Collet', 'Anne', 'acollet@example.com'),
    ('effecteur-cardio-1', 'bfaure', 'Faure', 'Benoît', 'bfaure@example.com'),
    ('effecteur-kine-1', 'Martin', 'Julie', 'jmartin', 'julie.martin@kine.com'),
    ('effecteur-neuro-1', 'Durand', 'Alain', 'adurand', 'alain.durand@neuro.com');

-- UTILISATEUR : adresse
INSERT INTO utilisateur.adresses (id, adresse, ville, code_postal, pays) VALUES
    ('adresse-effecteur-med-1', '12 rue Pasteur', 'Lyon', '69000', 'FRANCE'),
    ('adresse-effecteur-inf-1', '5 avenue Gambetta', 'Lyon', '69000', 'FRANCE'),
    ('adresse-effecteur-cardio-1', '8 bd Diderot', 'Lyon', '69000', 'FRANCE'),
    ('adresse-effecteur-kine-1', '12 rue des Massages', 'Lyon', '69000', 'FRANCE'),
    ('adresse-effecteur-neuro-1', '9 avenue du Cerveau', 'Lyon', '69000', 'FRANCE'),
    ('adresse-patient-1', '12 rue des Lilas', 'Lyon', '69000', 'FRANCE'),
    ('adresse-patient-2', '9 rue de la Paix', 'Lyon', '69000', 'FRANCE');

-- UTILISATEUR : patients
INSERT INTO utilisateur.patients (id, adresse, age, sexe, profession, date_naissance, numero_telephone, numero_securite_social) VALUES
    ('patient-1', 'adresse-patient-1', 55, 'Homme', 'Retraité', '1968-07-15', '0601020304', '184055512345698'),
    ('patient-2', 'adresse-patient-2', 48, 'Femme', 'Cadre', '1976-03-22', '0605060708', '248096789123456');

-- UTILISATEUR : professionnels / effecteurs
INSERT INTO utilisateur.effecteurs (id, adresse_professionnel, numero_professionnel, specialite) VALUES
    ('effecteur-med-1', 'adresse-effecteur-med-1', '0606060601', 'Médecin généraliste'),
    ('effecteur-inf-1', 'adresse-effecteur-inf-1', '0606060602','Infirmier'),
    ('effecteur-cardio-1', 'adresse-effecteur-cardio-1', '0606060603','Cardiologue'),
    ('effecteur-kine-1', 'adresse-effecteur-kine-1', '0606060604','Kinésithérapeute'),
    ('effecteur-neuro-1', 'adresse-effecteur-neuro-1', '0606060605','Neurologue');