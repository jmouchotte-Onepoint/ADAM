-- SANTE
INSERT INTO sante.containers (id,parcours_id, utlisateur_id) VALUES
    ('container-parcours-patient-1','parcours-patient-1', 'patient-1'),
    ('container-parcours-patient-2','parcours-patient-2', 'patient-2');

-- FICHES BIOLOGIQUES
INSERT INTO sante.fiches (id, type, etape_id, patient_id, document_id, nom, observation, resultats) VALUES
    ('fiche-generique-biologique-patient-1-etape-1', 'BIOLOGIQUE', 'parcours-patient-1-etape-1', 'patient-1', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 1 - patient 1',
    jsonb_build_object('taux_cholesterol_ldl', 1.8, 'triglycerides_tg', 1.3, 'glycemie_a_jeun', 1.10, 'hba1c', 6.5, 'creatinine', 95, 'dfg', 85, 'observation', 'Dyslipidémie légère, prédiabète probable')),
    ('fiche-generique-biologique-patient-1-etape-2', 'BIOLOGIQUE','parcours-patient-1-etape-2', 'patient-1', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 2 - patient 1',
    jsonb_build_object('taux_cholesterol_ldl', 1.7, 'triglycerides_tg', 1.2, 'glycemie_a_jeun', 1.08, 'hba1c', 6.4, 'creatinine', 96, 'dfg', 84, 'observation', 'Légère amélioration mais toujours en prédiabète')),
    ('fiche-generique-biologique-patient-1-etape-3', 'BIOLOGIQUE','parcours-patient-1-etape-3', 'patient-1', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 3 - patient 1',
    jsonb_build_object('taux_cholesterol_ldl', 1.6, 'triglycerides_tg', 1.2, 'glycemie_a_jeun', 1.05, 'hba1c', 6.2, 'creatinine', 97, 'dfg', 88, 'observation', 'Stabilisation, mais les facteurs de risque restent présents')),
    ('fiche-generique-biologique-patient-1-etape-4', 'BIOLOGIQUE','parcours-patient-1-etape-4', 'patient-1', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 4 - patient 1',
    jsonb_build_object('taux_cholesterol_ldl', 1.6, 'triglycerides_tg', 1.1, 'glycemie_a_jeun', 1.00, 'hba1c', 6.0, 'creatinine', 98, 'dfg', 90, 'observation', 'Stabilisation des paramètres biologiques mais obésité persistante')),
    ('fiche-generique-biologique-patient-2-etape-1', 'BIOLOGIQUE','parcours-patient-2-etape-1', 'patient-2', null, 'FicheEntity biologique', 'RésultatDonnées biologiques - étape 1 - patient 2',
    jsonb_build_object('taux_cholesterol_ldl', 1.9, 'triglycerides_tg', 1.4, 'glycemie_a_jeun', 1.12, 'hba1c', 6.8, 'creatinine', 100, 'dfg', 80, 'observation', 'Obésité avec risque élevé de diabète')),
    ('fiche-generique-biologique-patient-2-etape-2', 'BIOLOGIQUE','parcours-patient-2-etape-2', 'patient-2', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 2 - patient 2',
    jsonb_build_object('taux_cholesterol_ldl', 1.8, 'triglycerides_tg', 1.3, 'glycemie_a_jeun', 1.05, 'hba1c', 6.4, 'creatinine', 98, 'dfg', 82, 'observation', 'Amélioration des taux de cholestérol et de glycemie')),
    ('fiche-generique-biologique-patient-2-etape-3', 'BIOLOGIQUE','parcours-patient-2-etape-3', 'patient-2', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 3 - patient 2',
    jsonb_build_object('taux_cholesterol_ldl', 1.6, 'triglycerides_tg', 1.2, 'glycemie_a_jeun', 0.98, 'hba1c', 6.0, 'creatinine', 96, 'dfg', 85, 'observation', 'Perte de poids notable, amélioration des risques cardiaques et métaboliques')),
    ('fiche-generique-biologique-patient-2-etape-4', 'BIOLOGIQUE','parcours-patient-2-etape-4', 'patient-2', null, 'FicheEntity biologique', 'Résultat Données biologiques - étape 4 - patient 2',
    jsonb_build_object('taux_cholesterol_ldl', 1.4, 'triglycerides_tg', 1.1, 'glycemie_a_jeun', 0.90, 'hba1c', 5.8, 'creatinine', 94, 'dfg', 88, 'observation', 'Normalisation des paramètres biologiques, obésité contrôlée'));

-- FICHES CLINIQUES
INSERT INTO sante.fiches (id, type, etape_id, patient_id, document_id, nom, observation, resultats) VALUES
    ('fiche-generique-clinique-patient-1-etape-1', 'CLINIQUE','parcours-patient-1-etape-1', 'patient-1', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 1 - patient 1',
    jsonb_build_object('taille_cm', 172, 'poids_kg', 95, 'imc', 32.1, 'frequence_cardiaque', 78, 'pression_arterielle_systolique', 135, 'pression_arterielle_diastolique', 85, 'temperature', 36.9, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', true, 'observation', 'Obésité persistante')),
    ('fiche-generique-clinique-patient-1-etape-2', 'CLINIQUE','parcours-patient-1-etape-2', 'patient-1', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 2 - patient 1',
    jsonb_build_object('taille_cm', 172, 'poids_kg', 94, 'imc', 31.8, 'frequence_cardiaque', 76, 'pression_arterielle_systolique', 130, 'pression_arterielle_diastolique', 82, 'temperature', 36.8, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', true, 'observation', 'Légère amélioration, mais obésité toujours présente')),
    ('fiche-generique-clinique-patient-1-etape-3', 'CLINIQUE','parcours-patient-1-etape-3', 'patient-1', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 3 - patient 1',
    jsonb_build_object('taille_cm', 172, 'poids_kg', 93, 'imc', 31.4, 'frequence_cardiaque', 74, 'pression_arterielle_systolique', 128, 'pression_arterielle_diastolique', 80, 'temperature', 36.7, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', true, 'observation', 'État stable, IMC élevé')),
    ('fiche-generique-clinique-patient-1-etape-4', 'CLINIQUE','parcours-patient-1-etape-4', 'patient-1', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 4 - patient 1',
    jsonb_build_object('taille_cm', 172, 'poids_kg', 92, 'imc', 31.1, 'frequence_cardiaque', 74, 'pression_arterielle_systolique', 128, 'pression_arterielle_diastolique', 80, 'temperature', 36.7, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', true, 'observation', 'Obésité toujours présente')),
    ('fiche-generique-clinique-patient-2-etape-1', 'CLINIQUE','parcours-patient-2-etape-1', 'patient-2', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 1 - patient 2',
    jsonb_build_object('taille_cm', 165, 'poids_kg', 85, 'imc', 31.2, 'frequence_cardiaque', 78, 'pression_arterielle_systolique', 135, 'pression_arterielle_diastolique', 85, 'temperature', 36.9, 'fumeur', true, 'nombre_paquet_an', 10, 'hypertension', true, 'observation', 'Obésité de classe 1')),
    ('fiche-generique-clinique-patient-2-etape-2', 'CLINIQUE','parcours-patient-2-etape-2', 'patient-2', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 2 - patient 2',
    jsonb_build_object('taille_cm', 165, 'poids_kg', 75, 'imc', 27.5, 'frequence_cardiaque', 74, 'pression_arterielle_systolique', 128, 'pression_arterielle_diastolique', 82, 'temperature', 36.8, 'fumeur', true, 'nombre_paquet_an', 5, 'hypertension', false, 'observation', 'Perte de poids significative')),
    ('fiche-generique-clinique-patient-2-etape-3', 'CLINIQUE','parcours-patient-2-etape-3', 'patient-2', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 3 - patient 2',
    jsonb_build_object('taille_cm', 165, 'poids_kg', 68, 'imc', 25.0, 'frequence_cardiaque', 70, 'pression_arterielle_systolique', 122, 'pression_arterielle_diastolique', 78, 'temperature', 36.7, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', false, 'observation', 'Proche de la normale')),
    ('fiche-generique-clinique-patient-2-etape-4', 'CLINIQUE','parcours-patient-2-etape-4', 'patient-2', null, 'FicheEntity clinique', 'Résultat Données cliniques - étape 4 - patient 2',
    jsonb_build_object('taille_cm', 165, 'poids_kg', 63, 'imc', 23.1, 'frequence_cardiaque', 68, 'pression_arterielle_systolique', 120, 'pression_arterielle_diastolique', 75, 'temperature', 36.6, 'fumeur', false, 'nombre_paquet_an', null, 'hypertension', false, 'observation', 'Retour à un poids santé'));

-- FICHES QUALITÉ DE VIE
INSERT INTO sante.fiches (id, type, etape_id, patient_id, document_id, nom, observation, resultats) VALUES
    ('fiche-generique-qdv-patient-1-etape-1', 'QUALITE_VIE','parcours-patient-1-etape-1', 'patient-1', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 1 - patient 1',
    jsonb_build_object('score_mobilite', 2, 'score_douleur', 3, 'score_activite_usuelle', 3, 'score_anxiete', 2, 'score_depression', 2, 'observation', 'Mobilité réduite, obésité persistante')),
    ('fiche-generique-qdv-patient-1-etape-2', 'QUALITE_VIE','parcours-patient-1-etape-2', 'patient-1', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 2 - patient 1',
    jsonb_build_object('score_mobilite', 3, 'score_douleur', 4, 'score_activite_usuelle', 4, 'score_anxiete', 2, 'score_depression', 3, 'observation', 'Douleurs articulaires, fatigue')),
    ('fiche-generique-qdv-patient-1-etape-3', 'QUALITE_VIE','parcours-patient-1-etape-3', 'patient-1', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 3 - patient 1',
    jsonb_build_object('score_mobilite', 3, 'score_douleur', 3, 'score_activite_usuelle', 4, 'score_anxiete', 2, 'score_depression', 2, 'observation', 'Situation stable')),
    ('fiche-generique-qdv-patient-1-etape-4', 'QUALITE_VIE','parcours-patient-1-etape-4', 'patient-1', null, 'FicheEntity qualité de vie', 'RésultatQualité de vie - étape 4 - patient 1',
    jsonb_build_object('score_mobilite', 3, 'score_douleur', 4, 'score_activite_usuelle', 4, 'score_anxiete', 3, 'score_depression', 3, 'observation', 'Moral affecté par manque de progrès')),
    ('fiche-generique-qdv-patient-2-etape-1', 'QUALITE_VIE','parcours-patient-2-etape-1', 'patient-2', null, 'FicheEntity qualité de vie', 'Qualité de vie - étape 1 - patient 2',
    jsonb_build_object('score_mobilite', 3, 'score_douleur', 3, 'score_activite_usuelle', 3, 'score_anxiete', 2, 'score_depression', 2, 'observation', 'Limitations quotidiennes')),
    ('fiche-generique-qdv-patient-2-etape-2', 'QUALITE_VIE','parcours-patient-2-etape-2', 'patient-2', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 2 - patient 2',
    jsonb_build_object('score_mobilite', 2, 'score_douleur', 2, 'score_activite_usuelle', 2, 'score_anxiete', 1, 'score_depression', 1, 'observation', 'Amélioration sensible')),
    ('fiche-generique-qdv-patient-2-etape-3', 'QUALITE_VIE','parcours-patient-2-etape-3', 'patient-2', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 3 - patient 2',
    jsonb_build_object('score_mobilite', 1, 'score_douleur', 1, 'score_activite_usuelle', 1, 'score_anxiete', 1, 'score_depression', 1, 'observation', 'Qualité de vie normale')),
    ('fiche-generique-qdv-patient-2-etape-4', 'QUALITE_VIE','parcours-patient-2-etape-4', 'patient-2', null, 'FicheEntity qualité de vie', 'Résultat Qualité de vie - étape 4 - patient 2',
    jsonb_build_object('score_mobilite', 0, 'score_douleur', 0, 'score_activite_usuelle', 0, 'score_anxiete', 0, 'score_depression', 0, 'observation', 'Rétablissement complet, bonne vitalité'));

INSERT INTO sante.objets (id, nom, container_id, user_id) VALUES
    ('objet-fiche-generique-biologique-patient-1-etape-1','objet-1','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-clinique-patient-1-etape-1','objet-2','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-qdv-patient-1-etape-1','objet-3','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-biologique-patient-1-etape-2','objet-4','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-clinique-patient-1-etape-2','objet-5','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-qdv-patient-1-etape-2','objet-6','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-biologique-patient-1-etape-3','objet-7','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-clinique-patient-1-etape-3','objet-8','container-parcours-patient-1', 'patient-1'),
    ('objet-fiche-generique-qdv-patient-1-etape-3','objet-9','container-parcours-patient-1', 'patient-1');