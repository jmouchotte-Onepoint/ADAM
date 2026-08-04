-- PARCOURS : infos
INSERT INTO parcours.infos (id, nom, patient_id, pathologie, date_creation, date_fin, observation) VALUES
    ('parcours-patient-1', 'Pacours Diabétique','patient-1', 'DIABETE', '2023-01-01', '2023-12-31', 'Suivi du diabète'),
    ('parcours-patient-2', 'Parcours Obésité','patient-2', 'OBESITE','2024-01-15', '2024-12-15', 'Suivi post-AVC');

-- PARCOURS : referents
INSERT INTO parcours.referents (parcours_id, referent_id) VALUES
    ('parcours-patient-1', 'effecteur-med-1'),
    ('parcours-patient-2', 'effecteur-inf-1');

-- PARCOURS : etapes
INSERT INTO parcours.etapes (id, parcours_id, nom, date_creation, date_fin, observation) VALUES
    ('parcours-patient-1-etape-1', 'parcours-patient-1', 'Bilan initial', '2023-01-01', '2023-01-07', ''),
    ('parcours-patient-1-etape-2', 'parcours-patient-1', 'Consultation cardiologue', '2023-02-01', '2023-02-05', ''),
    ('parcours-patient-1-etape-3', 'parcours-patient-1', 'Bilan sanguin', '2023-03-01', '2023-03-02', ''),
    ('parcours-patient-1-etape-4', 'parcours-patient-1', 'Suivi mensuel', '2023-04-01', '2023-04-01', ''),
    ('parcours-patient-2-etape-1', 'parcours-patient-2', 'Bilan initial', '2024-01-16', '2024-01-17', ''),
    ('parcours-patient-2-etape-2', 'parcours-patient-2', 'Suivi kiné', '2024-03-01', '2024-03-30', ''),
    ('parcours-patient-2-etape-3', 'parcours-patient-2', 'Consultation neuro', '2024-09-01', '2024-09-01', ''),
    ('parcours-patient-2-etape-4', 'parcours-patient-2', 'Bilan final', '2024-12-10', '2024-12-10', '');

-- PARCOURS : invites
INSERT INTO parcours.invites (etape_id, invite_id) VALUES
    ('parcours-patient-1-etape-1', 'effecteur-med-1'),
    ('parcours-patient-1-etape-2','effecteur-cardio-1'),
    ('parcours-patient-1-etape-3','effecteur-inf-1'),
    ('parcours-patient-1-etape-4','effecteur-med-1'),
    ('parcours-patient-2-etape-1','effecteur-med-1'),
    ('parcours-patient-2-etape-2','effecteur-kine-1'),
    ('parcours-patient-2-etape-3','effecteur-neuro-1'),
    ('parcours-patient-2-etape-4','effecteur-med-1');