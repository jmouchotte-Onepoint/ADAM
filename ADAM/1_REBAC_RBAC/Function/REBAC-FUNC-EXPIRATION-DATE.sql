-- Une seule fois par base
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Fonction de clean_up
-- La colonne expires_at est déclarée dans les CREATE TABLE (REBAC-RELATIONS / ROLES / PERMISSIONS)
CREATE OR REPLACE FUNCTION cleanup_expired()
    RETURNS void AS $$
BEGIN
    DELETE FROM relations WHERE expires_at IS NOT NULL AND expires_at < NOW();
    DELETE FROM roles WHERE expires_at IS NOT NULL AND expires_at < NOW();
    DELETE FROM permissions WHERE expires_at IS NOT NULL AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER;

-- Toutes les heures à la minute 0
-- SELECT cron.schedule('deleted_expired_rrp','0 * * * *','SELECT cleanup_expired();');
