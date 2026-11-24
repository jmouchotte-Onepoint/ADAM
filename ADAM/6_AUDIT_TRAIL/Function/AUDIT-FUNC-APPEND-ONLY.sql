-- 1. Refus de toute modification du journal
-- Le propriétaire peut retirer le trigger : c'est la chaîne de hachage qui sert
-- de détection, pas cette fonction.
CREATE OR REPLACE FUNCTION fn_audit_log_is_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '[P40001] audit_log is append-only (attempted %)', TG_OP;
END;
$$ LANGUAGE plpgsql;
