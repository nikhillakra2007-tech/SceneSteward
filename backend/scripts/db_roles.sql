-- SceneSteward — database role bootstrap (run as a superuser or the schema owner).
-- The migration creates the ROLES with NOLOGIN; this script gives them LOGIN + passwords.
-- Usage:
--   psql "postgresql://SUPERUSER@HOST/DBNAME" \
--        -v app_password="$APP_PW" -v readonly_password="$RO_PW" -f scripts/db_roles.sql
-- Passwords are never stored in the repository.

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_app') THEN
        CREATE ROLE scenesteward_app NOLOGIN NOBYPASSRLS NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_readonly') THEN
        CREATE ROLE scenesteward_readonly NOLOGIN NOBYPASSRLS NOINHERIT;
    END IF;
END $$;

ALTER ROLE scenesteward_app LOGIN PASSWORD :'app_password';
ALTER ROLE scenesteward_readonly LOGIN PASSWORD :'readonly_password';

-- Report what was configured (no secret values are printed).
SELECT rolname, rolcanlogin, rolsuper, rolbypassrls
  FROM pg_roles
 WHERE rolname IN ('scenesteward_app', 'scenesteward_readonly', 'scenesteward')
 ORDER BY 1;
