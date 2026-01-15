-- ProManage MySQL Schema with Typed Columns
-- Execute with: mysql -u root -p promanage < mysql_schema.sql

-- Drop existing tables (in correct order due to foreign keys)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS property_suppliers;
DROP TABLE IF EXISTS renters;
DROP TABLE IF EXISTS user_supplier_credentials;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS properties;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- USERS TABLE
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role ENUM('admin', 'landlord') NOT NULL DEFAULT 'landlord',
    password_hash VARCHAR(255) NULL,
    oauth_provider ENUM('google', 'facebook') NULL,
    oauth_id VARCHAR(255) NULL,
    subscription_tier INT DEFAULT 0,
    subscription_expires DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_oauth (oauth_provider, oauth_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PROPERTIES TABLE
CREATE TABLE properties (
    id VARCHAR(36) PRIMARY KEY,
    landlord_id VARCHAR(36) NOT NULL,
    address TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_properties_landlord (landlord_id),
    INDEX idx_properties_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- RENTERS TABLE
CREATE TABLE renters (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(50) NULL,
    rent_day INT NULL,
    start_contract_date DATE NULL,
    rent_amount_eur FLOAT NULL,
    access_token VARCHAR(36) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    INDEX idx_renters_property (property_id),
    INDEX idx_renters_token (access_token),
    INDEX idx_renters_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- SUPPLIERS TABLE
CREATE TABLE suppliers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    has_api BOOLEAN DEFAULT FALSE,
    bill_type ENUM('rent', 'utilities', 'telecom', 'ebloc', 'other') DEFAULT 'utilities',
    extraction_pattern_supplier VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_suppliers_name (name),
    INDEX idx_suppliers_pattern (extraction_pattern_supplier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- USER_SUPPLIER_CREDENTIALS TABLE (for API credentials)
CREATE TABLE user_supplier_credentials (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    supplier_id VARCHAR(36) NOT NULL,
    username VARCHAR(255) NULL,
    password_hash VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_usc_user_supplier (user_id, supplier_id),
    INDEX idx_usc_user (user_id),
    INDEX idx_usc_supplier (supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PROPERTY_SUPPLIERS TABLE (must be before bills!)
CREATE TABLE property_suppliers (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL,
    supplier_id VARCHAR(36) NOT NULL,
    extraction_pattern_supplier VARCHAR(255) NULL,
    contract_id VARCHAR(100) NULL,
    direct_debit BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    INDEX idx_ps_property (property_id),
    INDEX idx_ps_supplier (supplier_id),
    INDEX idx_ps_contract (contract_id),
    INDEX idx_ps_extraction_pattern (extraction_pattern_supplier),
    UNIQUE INDEX idx_ps_property_supplier (property_id, supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- BILLS TABLE (after property_suppliers!)
CREATE TABLE bills (
    id VARCHAR(36) PRIMARY KEY,
    property_id VARCHAR(36) NOT NULL,
    renter_id VARCHAR(36) NULL,
    property_supplier_id VARCHAR(36) NULL,
    bill_type ENUM('rent', 'utilities', 'telecom', 'ebloc', 'other') NOT NULL,
    description TEXT NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(10) DEFAULT 'RON',
    due_date DATETIME NOT NULL,
    bill_date DATETIME NULL,
    legal_name VARCHAR(255) NULL,
    iban VARCHAR(50) NULL,
    bill_number VARCHAR(100) NULL,
    extraction_pattern_id VARCHAR(36) NULL,
    contract_id VARCHAR(100) NULL,
    payment_details TEXT NULL,
    status ENUM('pending', 'paid', 'overdue') DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
    FOREIGN KEY (property_supplier_id) REFERENCES property_suppliers(id) ON DELETE SET NULL,
    INDEX idx_bills_property (property_id),
    INDEX idx_bills_renter (renter_id),
    INDEX idx_bills_property_supplier (property_supplier_id),
    INDEX idx_bills_due_date (due_date),
    INDEX idx_bills_status (status),
    INDEX idx_bills_type (bill_type),
    INDEX idx_bills_contract (contract_id),
    INDEX idx_bills_property_due (property_id, due_date),
    INDEX idx_bills_property_status (property_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- PAYMENTS TABLE
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    bill_id VARCHAR(36) NOT NULL,
    amount FLOAT NOT NULL,
    method ENUM('bank_transfer', 'payment_service') NOT NULL,
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    commission FLOAT DEFAULT 0.0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    INDEX idx_payments_bill (bill_id),
    INDEX idx_payments_status (status),
    INDEX idx_payments_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- USER_PREFERENCES TABLE
CREATE TABLE user_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE,
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
    property_order TEXT NULL COMMENT 'JSON array of property IDs for display order preference',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_prefs_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- NOTE: extraction_patterns table has been removed - patterns are now stored as JSON files
