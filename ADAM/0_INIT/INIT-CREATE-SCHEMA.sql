-- 1. Creation du schéma if not exists
DO $$
BEGIN
	EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', current_schema());
END $$;