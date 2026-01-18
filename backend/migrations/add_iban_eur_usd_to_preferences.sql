-- Migration: Add iban_eur and iban_usd columns to user_preferences table
-- Date: 2026-01-18
-- Description: Adds EUR and USD IBAN fields for multi-currency rent payments
-- Works for both MySQL and SQLite

-- Add iban_eur column (RON IBAN for rent payments)
ALTER TABLE user_preferences ADD COLUMN iban_eur VARCHAR(50) DEFAULT NULL;

-- Add iban_usd column (USD IBAN for rent payments)
ALTER TABLE user_preferences ADD COLUMN iban_usd VARCHAR(50) DEFAULT NULL;
