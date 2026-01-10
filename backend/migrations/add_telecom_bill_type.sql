-- Migration: Add 'telecom' to bill_type enum
-- Run this migration to add the new bill type to existing databases
USE ultrafinu_promanage;

-- MySQL version: Modify ENUM to include 'telecom'
-- Note: This requires recreating the column or using ALTER MODIFY

-- Update suppliers table
ALTER TABLE suppliers MODIFY COLUMN bill_type ENUM('rent', 'utilities', 'telecom', 'ebloc', 'other') DEFAULT 'utilities';

-- Update bills table
ALTER TABLE bills MODIFY COLUMN bill_type ENUM('rent', 'utilities', 'telecom', 'ebloc', 'other') NOT NULL;

-- SQLite version (no action needed - SQLite uses CHECK constraints which are not enforced strictly,
-- but for new databases, the schema file has been updated)

