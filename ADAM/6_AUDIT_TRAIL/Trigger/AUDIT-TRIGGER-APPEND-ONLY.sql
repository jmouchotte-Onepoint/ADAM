-- 1. UPDATE, DELETE et TRUNCATE sur le journal échouent
DROP TRIGGER IF EXISTS trg_audit_log_append_only_row ON audit_log;
CREATE TRIGGER trg_audit_log_append_only_row
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log_is_append_only();

DROP TRIGGER IF EXISTS trg_audit_log_append_only_truncate ON audit_log;
CREATE TRIGGER trg_audit_log_append_only_truncate
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION fn_audit_log_is_append_only();
