-- Migration: Add amount_in_bill_currency and bill_currency fields to payment_notifications
-- Purpose: Store the payment amount converted to bill currency at time of payment for stable balance calculations
-- Date: 2026-01-22

-- SQLite version
-- Note: SQLite doesn't support IF NOT EXISTS for columns, so we use a try-catch approach in the application
-- These columns are nullable to maintain backward compatibility with existing records

-- Add amount_in_bill_currency column (payment amount converted to bill currency at time of payment)
ALTER TABLE payment_notifications ADD COLUMN amount_in_bill_currency REAL;

-- Add bill_currency column (bill's currency at time of payment for reference)
ALTER TABLE payment_notifications ADD COLUMN bill_currency TEXT;

-- MySQL version (run separately if using MySQL):
-- ALTER TABLE payment_notifications ADD COLUMN amount_in_bill_currency DECIMAL(10,2) DEFAULT NULL;
-- ALTER TABLE payment_notifications ADD COLUMN bill_currency VARCHAR(10) DEFAULT NULL;

-- PostgreSQL version (run separately if using PostgreSQL):
-- ALTER TABLE payment_notifications ADD COLUMN IF NOT EXISTS amount_in_bill_currency DECIMAL(10,2);
-- ALTER TABLE payment_notifications ADD COLUMN IF NOT EXISTS bill_currency VARCHAR(10);
