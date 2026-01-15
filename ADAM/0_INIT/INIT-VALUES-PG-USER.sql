DO $$
BEGIN
    EXECUTE format('SET app.adam.user_id = %L', current_user);
    EXECUTE format('ALTER ROLE %I SET app.adam.user_id TO %L', current_user, current_user);
END $$;

SET adam.user_attributes = '{}';