-- Migration: Replace payments table with payment_notifications table
-- This migration drops the old payments table (which was empty and designed for a different purpose)
-- and creates the new payment_notifications table for the renter-to-landlord payment confirmation feature
-- 
-- Run this migration on existing databases to add the pay notifications feature

-- For MySQL:
-- mysql -u root -p promanage < replace_payments_with_payment_notifications.sql

-- For PostgreSQL:
-- psql -U postgres -d promanage -f replace_payments_with_payment_notifications.sql

-- For SQLite:
-- sqlite3 promanage.db < replace_payments_with_payment_notifications.sql

-- ============================================
-- MySQL Version
-- ============================================
-- Uncomment the following section for MySQL:

-- DROP TABLE IF EXISTS payments;
-- 
-- CREATE TABLE payment_notifications (
--     id VARCHAR(36) PRIMARY KEY,
--     bill_id VARCHAR(36) NOT NULL,
--     renter_id VARCHAR(36) NOT NULL,
--     landlord_id VARCHAR(36) NOT NULL,
--     amount FLOAT NOT NULL,
--     currency VARCHAR(10) DEFAULT 'RON',
--     status ENUM('pending', 'confirmed', 'rejected') DEFAULT 'pending',
--     renter_note TEXT NULL COMMENT 'Optional note from renter about the payment',
--     landlord_note TEXT NULL COMMENT 'Optional note from landlord when confirming/rejecting',
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     confirmed_at DATETIME NULL COMMENT 'When landlord confirmed or rejected',
--     FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
--     FOREIGN KEY (renter_id) REFERENCES renters(id) ON DELETE CASCADE,
--     FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE,
--     INDEX idx_pn_bill (bill_id),
--     INDEX idx_pn_renter (renter_id),
--     INDEX idx_pn_landlord (landlord_id),
--     INDEX idx_pn_status (status),
--     INDEX idx_pn_created (created_at),
--     INDEX idx_pn_landlord_status (landlord_id, status)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- PostgreSQL Version
-- ============================================
-- Uncomment the following section for PostgreSQL:

-- DROP TABLE IF EXISTS payments CASCADE;
-- 
-- CREATE TABLE payment_notifications (
--     id VARCHAR(36) PRIMARY KEY,
--     bill_id VARCHAR(36) NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
--     renter_id VARCHAR(36) NOT NULL REFERENCES renters(id) ON DELETE CASCADE,
--     landlord_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
--     amount REAL NOT NULL,
--     currency VARCHAR(10) DEFAULT 'RON',
--     status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected')),
--     renter_note TEXT NULL,
--     landlord_note TEXT NULL,
--     created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     confirmed_at TIMESTAMP NULL
-- );
-- CREATE INDEX idx_pn_bill ON payment_notifications(bill_id);
-- CREATE INDEX idx_pn_renter ON payment_notifications(renter_id);
-- CREATE INDEX idx_pn_landlord ON payment_notifications(landlord_id);
-- CREATE INDEX idx_pn_status ON payment_notifications(status);
-- CREATE INDEX idx_pn_created ON payment_notifications(created_at);
-- CREATE INDEX idx_pn_landlord_status ON payment_notifications(landlord_id, status);

-- ============================================
-- SQLite Version (Active by default)
-- ============================================
-- SQLite doesn't support ENUM or CHECK constraints well, so we use TEXT

DROP TABLE IF EXISTS payments;

CREATE TABLE IF NOT EXISTS payment_notifications (
    id TEXT PRIMARY KEY,
    bill_id TEXT NOT NULL,
    renter_id TEXT NOT NULL,
    landlord_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'RON',
    status TEXT DEFAULT 'pending',  -- 'pending', 'confirmed', 'rejected'
    renter_note TEXT,  -- Optional note from renter about the payment
    landlord_note TEXT,  -- Optional note from landlord when confirming/rejecting
    created_at TEXT NOT NULL,
    confirmed_at TEXT,  -- When landlord confirmed or rejected
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    FOREIGN KEY (renter_id) REFERENCES renters(id) ON DELETE CASCADE,
    FOREIGN KEY (landlord_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pn_bill ON payment_notifications(bill_id);
CREATE INDEX IF NOT EXISTS idx_pn_renter ON payment_notifications(renter_id);
CREATE INDEX IF NOT EXISTS idx_pn_landlord ON payment_notifications(landlord_id);
CREATE INDEX IF NOT EXISTS idx_pn_status ON payment_notifications(status);
CREATE INDEX IF NOT EXISTS idx_pn_created ON payment_notifications(created_at);
CREATE INDEX IF NOT EXISTS idx_pn_landlord_status ON payment_notifications(landlord_id, status);
