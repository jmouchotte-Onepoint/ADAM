-- Une seule fois par base
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Ajout de la colonne spécifique
ALTER TABLE adam.relations ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE adam.roles ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE adam.permissions ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;

-- Fonction de clean_up
CREATE OR REPLACE FUNCTION adam.cleanup_expired()
    RETURNS void AS $$
BEGIN
    DELETE FROM adam.relations WHERE expires_at IS NOT NULL AND expires_at < NOW();
    DELETE FROM adam.roles WHERE expires_at IS NOT NULL AND expires_at < NOW();
    DELETE FROM adam.permissions WHERE expires_at IS NOT NULL AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER;

-- Toutes les heures à la minute 0
-- SELECT cron.schedule('deleted_expired_rrp','0 * * * *','SELECT adam.cleanup_expired();');