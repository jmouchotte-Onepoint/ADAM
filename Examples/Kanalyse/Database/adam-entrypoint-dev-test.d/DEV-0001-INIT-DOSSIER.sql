-- DOSSIER : insertions données
INSERT INTO qfq.dossier (id, nom, is_confidentiel, siret, type_entreprise, code_naf, tenant) VALUES
    ('dossier-1A', 'Dossier 1 Tenant A', 'false', '81245932100017', 'SAS', '47.11A', 'tenantA'),
    ('dossier-2A', 'Dossier 2 Tenant A', 'true', '52977498300025', 'SARL', '62.01Z', 'tenantA'),
    ('dossier-3A', 'Dossier 3 Tenant A', 'true', '67894211500066', 'SASU', '70.22Z', 'tenantA'),
    ('dossier-4A', 'Dossier 4 Tenant A', 'false', '89233477500012', 'SARL', '62.01Z', 'tenantA'),
    ('dossier-1B', 'Dossier 1 Tenant B', 'false', '90411368200039', 'EI', '56.10B', 'tenantB'),
    ('dossier-2B', 'Dossier 2 Tenant B', 'true', '30266854100058', 'EURL', '41.20A', 'tenantB');