-- Migration: Add property_order to user_preferences
-- This column stores a JSON array of property IDs representing the user's preferred display order

-- ============================================
-- PostgreSQL / Neon
-- ============================================
-- ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS property_order TEXT NULL;

-- ============================================
-- MySQL
-- ============================================
-- Check if column exists before adding (MySQL doesn't support IF NOT EXISTS for columns)
-- Run this:
-- ALTER TABLE user_preferences ADD COLUMN property_order TEXT NULL COMMENT 'JSON array of property IDs for display order preference';

-- ============================================
-- SQLite
-- ============================================
-- ALTER TABLE user_preferences ADD COLUMN property_order TEXT NULL;

-- Note: property_order stores a JSON array like '["prop-id-1", "prop-id-2"]'
-- The application code handles JSON serialization/deserialization
