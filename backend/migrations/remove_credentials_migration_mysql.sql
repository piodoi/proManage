-- MySQL Migration to remove user_supplier_credentials table and credential_id from property_suppliers
-- Run this migration to clean up credential-related data from existing MySQL databases

-- Select the database (change 'ultrafinu_promanage' to your database name if different)
USE ultrafinu_promanage;

-- Start transaction
START TRANSACTION;

-- Step 1: Check if the foreign key exists and drop it
-- Note: The foreign key name might vary, so we'll use a dynamic approach
-- First, let's check what the foreign key is called in your database

-- Get the constraint name (you can run this separately to see the name):
-- SELECT CONSTRAINT_NAME 
-- FROM information_schema.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'property_suppliers' 
-- AND COLUMN_NAME = 'credential_id' 
-- AND TABLE_SCHEMA = DATABASE();

-- Drop the foreign key constraint (replace 'property_suppliers_ibfk_3' with your actual constraint name if different)
-- You can find the constraint name by running: SHOW CREATE TABLE property_suppliers;
SET @constraint_name = (
    SELECT CONSTRAINT_NAME 
    FROM information_schema.KEY_COLUMN_USAGE 
    WHERE TABLE_NAME = 'property_suppliers' 
    AND COLUMN_NAME = 'credential_id' 
    AND REFERENCED_TABLE_NAME = 'user_supplier_credentials'
    AND TABLE_SCHEMA = DATABASE()
    LIMIT 1
);

SET @sql = IF(@constraint_name IS NOT NULL,
    CONCAT('ALTER TABLE property_suppliers DROP FOREIGN KEY ', @constraint_name),
    'SELECT "No foreign key to drop" AS Info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 2: Drop the credential_id column if it exists
SET @column_exists = (
    SELECT COUNT(*) 
    FROM information_schema.COLUMNS 
    WHERE TABLE_NAME = 'property_suppliers' 
    AND COLUMN_NAME = 'credential_id' 
    AND TABLE_SCHEMA = DATABASE()
);

SET @sql = IF(@column_exists > 0,
    'ALTER TABLE property_suppliers DROP COLUMN credential_id',
    'SELECT "Column credential_id does not exist" AS Info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 3: Drop the credential_id index if it exists
SET @index_exists = (
    SELECT COUNT(*) 
    FROM information_schema.STATISTICS 
    WHERE TABLE_NAME = 'property_suppliers' 
    AND INDEX_NAME = 'idx_ps_credential' 
    AND TABLE_SCHEMA = DATABASE()
);

SET @sql = IF(@index_exists > 0,
    'ALTER TABLE property_suppliers DROP INDEX idx_ps_credential',
    'SELECT "Index idx_ps_credential does not exist" AS Info'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 4: Drop user_supplier_credentials table if it exists
DROP TABLE IF EXISTS user_supplier_credentials;

-- Commit the transaction
COMMIT;

-- Verification queries (run these separately to verify the migration worked):
-- SHOW CREATE TABLE property_suppliers;
-- SHOW TABLES LIKE 'user_supplier_credentials';

