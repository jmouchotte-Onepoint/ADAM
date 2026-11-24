-- 1. Délégation d'identité (OWASP A01)
-- tenants_per_users lie un rôle PostgreSQL à ses tenants ; cette table fait la
-- même chose pour le sujet applicatif et ses attributs. La variable de session
-- app.adam.user_id ne fait que choisir parmi les lignes enregistrées ici, elle
-- ne peut plus déclarer une identité.
CREATE TABLE IF NOT EXISTS users_per_pg_user (
    pg_user VARCHAR(100) NOT NULL,
    user_id TEXT NOT NULL,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_attributes JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(user_attributes) = 'object'),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (pg_user, tenant_id, user_id)
);

-- 2. RLS activée ici, politiques dans Policy/ : elles appellent les fonctions
-- définies plus bas dans la couche.
ALTER TABLE users_per_pg_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants_per_users ENABLE ROW LEVEL SECURITY;
