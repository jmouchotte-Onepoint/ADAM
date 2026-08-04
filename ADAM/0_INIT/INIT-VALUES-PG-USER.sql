DO $$
BEGIN
    EXECUTE format('SET app.adam.user_id = %L', current_user);
END $$;

SET app.adam.user_attributes = '{}';