-- ProManage PostgreSQL Schema (Neon Compatible)
-- Execute using Neon MCP or psql

-- Drop existing tables (in correct order due to foreign keys)
DROP TABLE IF EXISTS payment_notifications CASCADE;
DROP TABLE IF EXISTS bills CASCADE;
DROP TABLE IF EXISTS property_suppliers CASCADE;
DROP TABLE IF EXISTS renters CASCADE;
DROP TABLE IF EXISTS user_supplier_credentials CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS properties CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- USERS TABLE
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'landlord' CHECK (role IN ('admin', 'landlord')),
    password_hash VARCHAR(255) NULL,
    oauth_provider VARCHAR(20) NULL CHECK (oauth_provider IN ('google', 'facebook')),
    oauth_id VARCHAR(255) NULL,
    subscription_tier INT DEFAULT 0,
    subscription_expires TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

-- PROPERTIES TABLE
CREATE TABLE properties (
    id VARCHAR(36) PRIMARY KEY,
    landlord_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_properties_landlord ON properties(landlord_id);
CREATE INDEX idx_properties_name ON properties(name);

-- RENTERS TABLE
CREATE TABLE renters (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(50) NULL,
    rent_day INT NULL,
    start_contract_date DATE NULL,
    rent_amount REAL NULL,
    rent_currency VARCHAR(10) DEFAULT 'EUR',
    access_token VARCHAR(36) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_renters_property ON renters(property_id);
CREATE INDEX idx_renters_token ON renters(access_token);
CREATE INDEX idx_renters_email ON renters(email);

-- SUPPLIERS TABLE
CREATE TABLE suppliers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    has_api BOOLEAN DEFAULT FALSE,
    bill_type VARCHAR(20) DEFAULT 'utilities' CHECK (bill_type IN ('rent', 'utilities', 'telecom', 'ebloc', 'other')),
    extraction_pattern_supplier VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_suppliers_name ON suppliers(name);
CREATE INDEX idx_suppliers_pattern ON suppliers(extraction_pattern_supplier);

-- USER_SUPPLIER_CREDENTIALS TABLE (for API credentials)
CREATE TABLE user_supplier_credentials (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    supplier_id VARCHAR(36) NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    username VARCHAR(255) NULL,
    password_hash VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, supplier_id)
);
CREATE INDEX idx_usc_user ON user_supplier_credentials(user_id);
CREATE INDEX idx_usc_supplier ON user_supplier_credentials(supplier_id);

-- PROPERTY_SUPPLIERS TABLE (must be before bills!)
CREATE TABLE property_suppliers (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    supplier_id VARCHAR(36) NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    extraction_pattern_supplier VARCHAR(255) NULL,
    contract_id VARCHAR(100) NULL,
    direct_debit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(property_id, supplier_id)
);
CREATE INDEX idx_ps_property ON property_suppliers(property_id);
CREATE INDEX idx_ps_supplier ON property_suppliers(supplier_id);
CREATE INDEX idx_ps_contract ON property_suppliers(contract_id);
CREATE INDEX idx_ps_extraction_pattern ON property_suppliers(extraction_pattern_supplier);

-- BILLS TABLE (after property_suppliers!)
CREATE TABLE bills (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    renter_id VARCHAR(36) NULL,
    property_supplier_id VARCHAR(36) NULL REFERENCES property_suppliers(id) ON DELETE SET NULL,
    bill_type VARCHAR(20) NOT NULL CHECK (bill_type IN ('rent', 'utilities', 'telecom', 'ebloc', 'other')),
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    currency VARCHAR(10) DEFAULT 'RON',
    due_date TIMESTAMP NOT NULL,
    bill_date TIMESTAMP NULL,
    legal_name VARCHAR(255) NULL,
    iban VARCHAR(50) NULL,
    bill_number VARCHAR(100) NULL,
    extraction_pattern_id VARCHAR(36) NULL,
    contract_id VARCHAR(100) NULL,
    payment_details TEXT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'overdue')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bills_property ON bills(property_id);
CREATE INDEX idx_bills_renter ON bills(renter_id);
CREATE INDEX idx_bills_property_supplier ON bills(property_supplier_id);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_type ON bills(bill_type);
CREATE INDEX idx_bills_contract ON bills(contract_id);
CREATE INDEX idx_bills_property_due ON bills(property_id, due_date);
CREATE INDEX idx_bills_property_status ON bills(property_id, status);

-- PAYMENT_NOTIFICATIONS TABLE
-- Stores payment claims from renters that landlords need to confirm
CREATE TABLE payment_notifications (
    id VARCHAR(36) PRIMARY KEY,
    bill_id VARCHAR(36) NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    renter_id VARCHAR(36) NOT NULL REFERENCES renters(id) ON DELETE CASCADE,
    landlord_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    currency VARCHAR(10) DEFAULT 'RON',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected')),
    renter_note TEXT NULL,  -- Optional note from renter about the payment
    landlord_note TEXT NULL,  -- Optional note from landlord when confirming/rejecting
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL  -- When landlord confirmed or rejected
);
CREATE INDEX idx_pn_bill ON payment_notifications(bill_id);
CREATE INDEX idx_pn_renter ON payment_notifications(renter_id);
CREATE INDEX idx_pn_landlord ON payment_notifications(landlord_id);
CREATE INDEX idx_pn_status ON payment_notifications(status);
CREATE INDEX idx_pn_created ON payment_notifications(created_at);
CREATE INDEX idx_pn_landlord_status ON payment_notifications(landlord_id, status);

-- USER_PREFERENCES TABLE
CREATE TABLE user_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    language VARCHAR(10) DEFAULT 'en',
    view_mode VARCHAR(20) DEFAULT 'list',
    rent_warning_days INT DEFAULT 5,
    rent_currency VARCHAR(10) DEFAULT 'EUR',
    bill_currency VARCHAR(10) DEFAULT 'RON',
    date_format VARCHAR(20) DEFAULT 'DD/MM/YYYY',
    phone_number VARCHAR(50) NULL,
    landlord_name VARCHAR(255) NULL,
    personal_email VARCHAR(255) NULL,
    iban VARCHAR(50) NULL,
    property_order TEXT NULL,  -- JSON array of property IDs for display order preference
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_prefs_user ON user_preferences(user_id);

-- NOTE: extraction_patterns table has been removed - patterns are now stored as JSON files

