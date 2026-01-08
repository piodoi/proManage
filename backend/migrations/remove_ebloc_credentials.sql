-- Migration to remove ebloc_username and ebloc_password_hash from users table
-- Run this AFTER the remove_credentials_migration to complete the cleanup

-- For MySQL
-- USE ultrafinu_promanage;
-- 
-- START TRANSACTION;
-- 
-- -- Drop ebloc columns from users table
-- ALTER TABLE users DROP COLUMN ebloc_username;
-- ALTER TABLE users DROP COLUMN ebloc_password_hash;
-- 
-- COMMIT;

-- For SQLite (requires recreating the table):
-- This is complex for SQLite - only run if you need to clean up existing data
-- For new installations, just use the updated schema files

