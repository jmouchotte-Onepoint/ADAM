CREATE OR REPLACE FUNCTION adam.get_current_user_attributes()
RETURNS JSONB AS $$
    SELECT current_setting('app.adam.user_attributes', true)::jsonb;
$$ LANGUAGE SQL STABLE SECURITY INVOKER;

CREATE OR REPLACE FUNCTION adam.get_current_user_id()
RETURNS TEXT AS $$
    SELECT current_setting('app.adam.user_id',true)
$$ LANGUAGE SQL STABLE SECURITY INVOKER;

CREATE OR REPLACE FUNCTION adam.is_allow(prefix TEXT)
RETURNS BOOLEAN AS $$
    SELECT CURRENT_USER LIKE prefix || '_%';
$$ LANGUAGE sql STABLE PARALLEL SAFE;