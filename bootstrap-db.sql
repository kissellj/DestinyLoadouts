REVOKE CONNECT ON DATABASE alexa_destinyloadouts FROM public;
REVOKE CONNECT ON DATABASE bungie_destiny_world_sql_content FROM public;

\c alexa_destinyloadouts;
SELECT pid, pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = current_database() AND pid <> pg_backend_pid();

\c bungie_destiny_world_sql_content;
SELECT pid, pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = current_database() AND pid <> pg_backend_pid();

\c postgres;

DROP TABLE IF EXISTS public.loadouts;
DROP DATABASE IF EXISTS alexa_destinyloadouts;
DROP DATABASE IF EXISTS bungie_destiny_world_sql_content;
DROP DATABASE IF EXISTS bungie_destiny1_world_sql_content;

CREATE DATABASE alexa_destinyloadouts;
CREATE DATABASE bungie_destiny_world_sql_content;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'XXXXXXXXXXXXX') THEN
        CREATE ROLE bungie WITH LOGIN PASSWORD 'XXXXXXXXXXXX';
    END IF;
END
$$;

\c alexa_destinyloadouts;
CREATE TABLE IF NOT EXISTS public.alexa_speak (
      card_title CHARACTER VARYING(256),
      speech TEXT,
      timestamp TIMESTAMP );

CREATE TABLE IF NOT EXISTS public.loadouts (
      membership_id_bungie INTEGER NOT NULL,
      display_name CHARACTER VARYING(32),
      membership_type SMALLINT,
      membership_id BIGINT,
      character_id BIGINT,
      character_race BIGINT,
      character_gender BIGINT,
      character_class BIGINT,
      loadout_name CHARACTER VARYING(256),
      equipped_items TEXT,
      timestamp TIMESTAMP );
GRANT ALL PRIVILEGES ON SCHEMA public TO bungie;
GRANT ALL PRIVILEGES ON DATABASE alexa_destinyloadouts TO bungie;

ALTER TABLE public.alexa_speak OWNER TO bungie;
ALTER TABLE public.loadouts OWNER TO bungie;

\c bungie_destiny_world_sql_content;
GRANT ALL PRIVILEGES ON SCHEMA public TO bungie;
GRANT ALL PRIVILEGES ON DATABASE bungie_destiny_world_sql_content TO bungie;

\c postgres;

