-- Migration: Add extraction_pattern_supplier to property_suppliers table
-- This column allows property-only suppliers from text patterns (supplier_id = 0)
-- Run this migration to add the new column to existing databases
USE ultrafinu_promanage;

-- SQLite version:
-- ALTER TABLE property_suppliers ADD COLUMN extraction_pattern_supplier TEXT;
-- CREATE INDEX IF NOT EXISTS idx_prop_supp_extraction_pattern ON property_suppliers(extraction_pattern_supplier);
-- INSERT OR IGNORE INTO suppliers (id, name, has_api, bill_type, created_at) VALUES ('0', '[Pattern-based Supplier]', 0, 'utilities', datetime('now'));


-- MySQL version:
ALTER TABLE property_suppliers ADD COLUMN extraction_pattern_supplier VARCHAR(255) NULL AFTER supplier_id;
CREATE INDEX idx_ps_extraction_pattern ON property_suppliers(extraction_pattern_supplier);

-- Create placeholder supplier for pattern-based property suppliers
INSERT IGNORE INTO suppliers (id, name, has_api, bill_type, created_at)
VALUES ('0', '[Pattern-based Supplier]', FALSE, 'utilities', NOW());

