CREATE SCHEMA IF NOT EXISTS adam;
ALTER ROLE postgres IN DATABASE adamdb SET search_path TO adam, public;
