\set ON_ERROR_STOP on

DO $do$
DECLARE
    v_username text := :'student_name';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_username) THEN
        RAISE EXCEPTION 'Role % does not exist', v_username;
    END IF;

    EXECUTE format('GRANT student_sandbox_owner TO %I', v_username);
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION %I', 'sandbox_' || v_username, v_username);
    EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', 'sandbox_' || v_username, v_username);
    EXECUTE format('ALTER ROLE %I IN DATABASE %I SET search_path = raw, %I', v_username, current_database(), 'sandbox_' || v_username);
END
$do$;

