-- Migration: Rename rent_amount_eur to rent_amount and add rent_currency column
-- This migration preserves existing data and sets rent_currency to 'EUR' for all existing records

-- MySQL Migration
-- Step 1: Add rent_currency column with default 'EUR'
ALTER TABLE renters ADD COLUMN rent_currency VARCHAR(10) DEFAULT 'EUR' AFTER rent_amount_eur;

-- Step 2: Rename rent_amount_eur to rent_amount
ALTER TABLE renters CHANGE COLUMN rent_amount_eur rent_amount FLOAT NULL;

-- Step 3: Update all existing records to have rent_currency = 'EUR' (in case any are NULL)
UPDATE renters SET rent_currency = 'EUR' WHERE rent_currency IS NULL;

-- Verify the changes
-- SELECT id, name, rent_amount, rent_currency FROM renters;
