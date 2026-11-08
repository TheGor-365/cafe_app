-- CI-only synthetic PostgreSQL roles: no private data or owner Docker involved.
-- Keep these DDL statements in lockstep with the SHA-verified local roles helper.
BEGIN;
CREATE ROLE cafe_synth_owner NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
CREATE ROLE cafe_synth_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN NOREPLICATION NOBYPASSRLS PASSWORD 'CIOnlySyntheticRolePass_20261105';
REVOKE ALL ON DATABASE cafe_synthetic FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO cafe_synth_owner;
GRANT CONNECT ON DATABASE cafe_synthetic TO cafe_synth_app;
GRANT USAGE ON SCHEMA public TO cafe_synth_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cafe_synth_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cafe_synth_app;
ALTER DEFAULT PRIVILEGES FOR ROLE cafe_synth_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO cafe_synth_app;
ALTER ROLE cafe_synth_app IN DATABASE cafe_synthetic SET search_path = public;
COMMIT;
