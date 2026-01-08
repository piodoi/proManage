-- SQLite Migration to remove user_supplier_credentials table and credential_id from property_suppliers
-- Run this migration to clean up credential-related data from existing SQLite databases

-- SQLite requires recreating the table to drop a column
BEGIN TRANSACTION;

-- Step 1: Create new property_suppliers table without credential_id
CREATE TABLE property_suppliers_new (
    id TEXT PRIMARY KEY,
    property_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    contract_id TEXT,
    direct_debit INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    UNIQUE(property_id, supplier_id, contract_id)
);

-- Step 2: Copy data from old table to new table (excluding credential_id)
INSERT INTO property_suppliers_new (id, property_id, supplier_id, contract_id, direct_debit, created_at, updated_at)
SELECT id, property_id, supplier_id, contract_id, direct_debit, created_at, updated_at
FROM property_suppliers;

-- Step 3: Drop old table
DROP TABLE property_suppliers;

-- Step 4: Rename new table to original name
ALTER TABLE property_suppliers_new RENAME TO property_suppliers;

-- Step 5: Recreate indexes
CREATE INDEX idx_prop_supp_property ON property_suppliers(property_id);
CREATE INDEX idx_prop_supp_supplier ON property_suppliers(supplier_id);
CREATE INDEX idx_prop_supp_contract ON property_suppliers(contract_id);
CREATE INDEX idx_prop_supp_direct_debit ON property_suppliers(direct_debit);

-- Step 6: Drop user_supplier_credentials table
DROP TABLE IF EXISTS user_supplier_credentials;

COMMIT;

