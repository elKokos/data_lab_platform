\set ON_ERROR_STOP on

DO $do$
DECLARE
    v_username text := :'student_name';
    v_password text := :'student_password';
    v_with_sandbox boolean := (:'with_sandbox')::boolean;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_username) THEN
        RAISE EXCEPTION 'Role % already exists', v_username;
    END IF;

    EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L IN ROLE student_readonly', v_username, v_password);

    IF v_with_sandbox THEN
        EXECUTE format('GRANT student_sandbox_owner TO %I', v_username);
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I AUTHORIZATION %I', 'sandbox_' || v_username, v_username);
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', 'sandbox_' || v_username, v_username);
        EXECUTE format('ALTER ROLE %I IN DATABASE %I SET search_path = raw, %I', v_username, current_database(), 'sandbox_' || v_username);
    END IF;
END
$do$;
