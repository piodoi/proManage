-- Migration: Rename supplier_id to property_supplier_id in bills table
-- This change links bills to PropertySupplier.id instead of Supplier.id
-- 
-- For existing data, the old supplier_id values will remain but now point to nothing
-- They are kept for historical reference, new bills will use the correct property_supplier_id

-- ============================================================================
-- MySQL Version
-- ============================================================================

-- Step 1: Drop the old foreign key constraint and index
-- Note: You may need to check the actual constraint name with:
-- SHOW CREATE TABLE bills;
ALTER TABLE bills DROP FOREIGN KEY bills_ibfk_2;  -- or whatever the constraint is named
ALTER TABLE bills DROP INDEX idx_bills_supplier;

-- Step 2: Rename the column
ALTER TABLE bills CHANGE COLUMN supplier_id property_supplier_id VARCHAR(36) NULL;

-- Step 3: Add new foreign key constraint pointing to property_suppliers table
ALTER TABLE bills ADD CONSTRAINT fk_bills_property_supplier 
    FOREIGN KEY (property_supplier_id) REFERENCES property_suppliers(id) ON DELETE SET NULL;

-- Step 4: Add new index
CREATE INDEX idx_bills_property_supplier ON bills(property_supplier_id);


-- ============================================================================
-- SQLite Version (SQLite doesn't support ALTER COLUMN, need to recreate table)
-- ============================================================================
-- For SQLite, you would need to:
-- 1. Create new table with renamed column
-- 2. Copy data
-- 3. Drop old table  
-- 4. Rename new table
--
-- But since existing supplier_id values won't match property_supplier ids anyway,
-- it's simpler to just add the new column:
--
-- ALTER TABLE bills ADD COLUMN property_supplier_id TEXT;
-- UPDATE bills SET property_supplier_id = NULL;  -- Clear old references, they were Supplier.id not PropertySupplier.id
-- 
-- The old supplier_id column can remain for historical reference but won't be used.

