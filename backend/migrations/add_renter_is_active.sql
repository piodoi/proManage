-- Migration: Add renters.is_active soft-delete flag
-- Date: 2026-09-02
-- Description: Preserve renter history by inactivating renters instead of deleting them.

ALTER TABLE renters ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Backfill existing rows defensively (for nullable legacy states).
UPDATE renters SET is_active = TRUE WHERE is_active IS NULL;
