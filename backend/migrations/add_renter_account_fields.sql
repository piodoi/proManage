-- Migration: Add renter account fields
-- Date: 2026-02-01
-- Description: Add password_hash, language, and email_notifications fields to renters table

-- Add password_hash for renter accounts (optional - NULL means no account created)
ALTER TABLE renters ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;

-- Add language preference (defaults to 'ro' for renters)
ALTER TABLE renters ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'ro';

-- Add email notifications opt-in (requires email to be set)
ALTER TABLE renters ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN DEFAULT FALSE;

-- Create index on email for looking up renters by email (for login)
CREATE INDEX IF NOT EXISTS idx_renters_email_login ON renters(email) WHERE email IS NOT NULL AND password_hash IS NOT NULL;
