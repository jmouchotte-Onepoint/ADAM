CREATE OR REPLACE FUNCTION adam.get_current_tenant_id()
    RETURNS text
    LANGUAGE SQL
    SECURITY INVOKER
AS $$
  SELECT tenant_id
  FROM adam.tenants_per_users
  WHERE pg_user = current_user
    AND tenant_id = current_setting('app.adam.tenant_id',true)
  LIMIT 1;
$$;