-- ProManage SQLite Schema with Typed Columns
-- Execute with: sqlite3 promanage_typed.db < sqlite_typed_schema.sql

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Drop existing tables (in correct order due to foreign keys)
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS renters;
DROP TABLE IF EXISTS property_suppliers;
DROP TABLE IF EXISTS user_supplier_credentials;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS properties;
DROP TABLE IF EXISTS users;

-- USERS TABLE
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'landlord' CHECK(role IN ('admin', 'landlord')),
    password_hash TEXT,
    oauth_provider TEXT CHECK(oauth_provider IN ('google', 'facebook')),
    oauth_id TEXT,
    subscription_tier INTEGER DEFAULT 0,
    subscription_expires TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

-- PROPERTIES TABLE
CREATE TABLE properties (
    id TEXT PRIMARY KEY,
    landlord_id TEXT NOT NULL,
    address TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_properties_landlord ON properties(landlord_id);
CREATE INDEX idx_properties_name ON properties(name);

-- RENTERS TABLE
CREATE TABLE renters (
    id TEXT PRIMARY KEY,
    property_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    rent_day INTEGER,
    start_contract_date TEXT,
    rent_amount_eur REAL,
    access_token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);

CREATE INDEX idx_renters_property ON renters(property_id);
CREATE INDEX idx_renters_token ON renters(access_token);
CREATE INDEX idx_renters_name ON renters(name);

-- SUPPLIERS TABLE
CREATE TABLE suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    has_api INTEGER NOT NULL DEFAULT 0,
    bill_type TEXT NOT NULL DEFAULT 'utilities' CHECK(bill_type IN ('rent', 'utilities', 'ebloc', 'other')),
    extraction_pattern_supplier TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_suppliers_name ON suppliers(name);
CREATE INDEX idx_suppliers_extraction ON suppliers(extraction_pattern_supplier);

-- BILLS TABLE
CREATE TABLE bills (
    id TEXT PRIMARY KEY,
    property_id TEXT NOT NULL,
    renter_id TEXT,
    supplier_id TEXT,
    bill_type TEXT NOT NULL DEFAULT 'utilities' CHECK(bill_type IN ('rent', 'utilities', 'ebloc', 'other')),
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'RON' CHECK(currency IN ('RON', 'EUR', 'USD')),
    due_date TEXT NOT NULL,
    bill_date TEXT,
    legal_name TEXT,
    iban TEXT,
    bill_number TEXT,
    extraction_pattern_id TEXT,
    contract_id TEXT,
    payment_details TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'paid', 'overdue', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (renter_id) REFERENCES renters(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);

CREATE INDEX idx_bills_property ON bills(property_id);
CREATE INDEX idx_bills_renter ON bills(renter_id);
CREATE INDEX idx_bills_supplier ON bills(supplier_id);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_bill_type ON bills(bill_type);
CREATE INDEX idx_bills_contract ON bills(contract_id);
CREATE INDEX idx_bills_extraction ON bills(extraction_pattern_id);

-- PAYMENTS TABLE
CREATE TABLE payments (
    id TEXT PRIMARY KEY,
    bill_id TEXT NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL DEFAULT 'bank_transfer' CHECK(method IN ('bank_transfer', 'payment_service')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed', 'cancelled')),
    commission REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);

CREATE INDEX idx_payments_bill ON payments(bill_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created ON payments(created_at);

-- PROPERTY SUPPLIERS TABLE
CREATE TABLE property_suppliers (
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

CREATE INDEX idx_prop_supp_property ON property_suppliers(property_id);
CREATE INDEX idx_prop_supp_supplier ON property_suppliers(supplier_id);
CREATE INDEX idx_prop_supp_contract ON property_suppliers(contract_id);
CREATE INDEX idx_prop_supp_direct_debit ON property_suppliers(direct_debit);

-- USER PREFERENCES TABLE
CREATE TABLE user_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL DEFAULT 'en',
    view_mode TEXT NOT NULL DEFAULT 'list',
    rent_warning_days INTEGER NOT NULL DEFAULT 5,
    rent_currency TEXT NOT NULL DEFAULT 'EUR',
    bill_currency TEXT NOT NULL DEFAULT 'RON',
    date_format TEXT NOT NULL DEFAULT 'DD/MM/YYYY',
    phone_number TEXT,
    landlord_name TEXT,
    personal_email TEXT,
    iban TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_prefs_user ON user_preferences(user_id);

