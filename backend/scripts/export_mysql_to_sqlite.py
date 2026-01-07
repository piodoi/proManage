#!/usr/bin/env python3
"""
Export MySQL data to SQLite-compatible SQL INSERT statements

Usage:
    cd backend
    poetry run python scripts/export_mysql_to_sqlite.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from sqlalchemy import create_engine, text
import json
from datetime import datetime

# Configure output encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def escape_sql_string(s):
    """Escape string for SQLite"""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''").replace("\\", "\\\\") + "'"

def format_datetime(dt):
    """Convert datetime to ISO 8601 string for SQLite"""
    if dt is None:
        return 'NULL'
    if isinstance(dt, str):
        return escape_sql_string(dt)
    return escape_sql_string(dt.strftime('%Y-%m-%dT%H:%M:%S'))

def export_mysql_to_sqlite():
    """Export MySQL data to SQLite SQL file"""
    
    # Get MySQL URL from environment
    mysql_url = os.environ.get("DATABASE_URL")
    if not mysql_url or not mysql_url.startswith("mysql"):
        print("ERROR: DATABASE_URL must point to MySQL database")
        print(f"Current: {mysql_url}")
        sys.exit(1)
    
    # Ensure pymysql driver
    if '+pymysql' not in mysql_url:
        mysql_url = mysql_url.replace('mysql://', 'mysql+pymysql://', 1)
    
    print(f"[Export] Connecting to MySQL...")
    engine = create_engine(mysql_url)
    
    output_file = Path(__file__).parent / 'sqlite_data_import.sql'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- ProManage Data Export from MySQL to SQLite\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("-- Import with: sqlite3 promanage.db < sqlite_data_import.sql\n\n")
        f.write("BEGIN TRANSACTION;\n\n")
        f.write("-- Disable foreign key checks during import\n")
        f.write("PRAGMA foreign_keys = OFF;\n\n")
        
        with engine.connect() as conn:
            # Export Users
            print("[Export] Exporting users...")
            result = conn.execute(text("SELECT * FROM users ORDER BY created_at"))
            users = result.fetchall()
            f.write(f"-- Users ({len(users)} records)\n")
            for row in users:
                f.write(f"INSERT INTO users (id, email, name, role, password_hash, oauth_provider, oauth_id, "
                       f"subscription_tier, subscription_expires, ebloc_username, ebloc_password_hash, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.email)},\n")
                f.write(f"  {escape_sql_string(row.name)},\n")
                f.write(f"  {escape_sql_string(row.role)},\n")
                f.write(f"  {escape_sql_string(row.password_hash)},\n")
                f.write(f"  {escape_sql_string(row.oauth_provider)},\n")
                f.write(f"  {escape_sql_string(row.oauth_id)},\n")
                f.write(f"  {row.subscription_tier if row.subscription_tier is not None else 0},\n")
                f.write(f"  {format_datetime(row.subscription_expires)},\n")
                f.write(f"  {escape_sql_string(row.ebloc_username)},\n")
                f.write(f"  {escape_sql_string(row.ebloc_password_hash)},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export Properties
            print("[Export] Exporting properties...")
            result = conn.execute(text("SELECT * FROM properties ORDER BY created_at"))
            properties = result.fetchall()
            f.write(f"-- Properties ({len(properties)} records)\n")
            for row in properties:
                f.write(f"INSERT INTO properties (id, landlord_id, address, name, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.landlord_id)},\n")
                f.write(f"  {escape_sql_string(row.address)},\n")
                f.write(f"  {escape_sql_string(row.name)},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export Renters
            print("[Export] Exporting renters...")
            result = conn.execute(text("SELECT * FROM renters ORDER BY created_at"))
            renters = result.fetchall()
            f.write(f"-- Renters ({len(renters)} records)\n")
            for row in renters:
                f.write(f"INSERT INTO renters (id, property_id, name, email, phone, rent_day, "
                       f"start_contract_date, rent_amount_eur, access_token, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.property_id)},\n")
                f.write(f"  {escape_sql_string(row.name)},\n")
                f.write(f"  {escape_sql_string(row.email)},\n")
                f.write(f"  {escape_sql_string(row.phone)},\n")
                f.write(f"  {row.rent_day if row.rent_day is not None else 'NULL'},\n")
                f.write(f"  {format_datetime(row.start_contract_date)},\n")
                f.write(f"  {row.rent_amount_eur if row.rent_amount_eur is not None else 'NULL'},\n")
                f.write(f"  {escape_sql_string(row.access_token)},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export Suppliers
            print("[Export] Exporting suppliers...")
            result = conn.execute(text("SELECT * FROM suppliers ORDER BY name"))
            suppliers = result.fetchall()
            f.write(f"-- Suppliers ({len(suppliers)} records)\n")
            for row in suppliers:
                f.write(f"INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.name)},\n")
                f.write(f"  {1 if row.has_api else 0},\n")
                f.write(f"  {escape_sql_string(row.bill_type)},\n")
                f.write(f"  {escape_sql_string(row.extraction_pattern_supplier)},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export Bills
            print("[Export] Exporting bills...")
            result = conn.execute(text("SELECT * FROM bills ORDER BY created_at"))
            bills = result.fetchall()
            f.write(f"-- Bills ({len(bills)} records)\n")
            for row in bills:
                f.write(f"INSERT INTO bills (id, property_id, renter_id, supplier_id, bill_type, description, "
                       f"amount, currency, due_date, bill_date, legal_name, iban, bill_number, "
                       f"extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.property_id)},\n")
                f.write(f"  {escape_sql_string(row.renter_id)},\n")
                f.write(f"  {escape_sql_string(row.supplier_id)},\n")
                f.write(f"  {escape_sql_string(row.bill_type)},\n")
                f.write(f"  {escape_sql_string(row.description)},\n")
                f.write(f"  {row.amount if row.amount is not None else 0},\n")
                f.write(f"  {escape_sql_string(row.currency)},\n")
                f.write(f"  {format_datetime(row.due_date)},\n")
                f.write(f"  {format_datetime(row.bill_date)},\n")
                f.write(f"  {escape_sql_string(row.legal_name)},\n")
                f.write(f"  {escape_sql_string(row.iban)},\n")
                f.write(f"  {escape_sql_string(row.bill_number)},\n")
                f.write(f"  {escape_sql_string(row.extraction_pattern_id)},\n")
                f.write(f"  {escape_sql_string(row.contract_id)},\n")
                f.write(f"  {escape_sql_string(row.payment_details)},\n")
                f.write(f"  {escape_sql_string(row.status)},\n")
                f.write(f"  {escape_sql_string(row.source_email_id)},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export Payments
            print("[Export] Exporting payments...")
            result = conn.execute(text("SELECT * FROM payments ORDER BY created_at"))
            payments = result.fetchall()
            f.write(f"-- Payments ({len(payments)} records)\n")
            for row in payments:
                f.write(f"INSERT INTO payments (id, bill_id, amount, method, status, commission, created_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.bill_id)},\n")
                f.write(f"  {row.amount if row.amount is not None else 0},\n")
                f.write(f"  {escape_sql_string(row.method)},\n")
                f.write(f"  {escape_sql_string(row.status)},\n")
                f.write(f"  {row.commission if row.commission is not None else 0},\n")
                f.write(f"  {format_datetime(row.created_at)}\n")
                f.write(");\n\n")
            
            # Export User Supplier Credentials
            print("[Export] Exporting user supplier credentials...")
            result = conn.execute(text("SELECT * FROM user_supplier_credentials ORDER BY created_at"))
            creds = result.fetchall()
            f.write(f"-- User Supplier Credentials ({len(creds)} records)\n")
            for row in creds:
                f.write(f"INSERT INTO user_supplier_credentials (id, user_id, supplier_id, username, password_hash, created_at, updated_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.user_id)},\n")
                f.write(f"  {escape_sql_string(row.supplier_id)},\n")
                f.write(f"  {escape_sql_string(row.username)},\n")
                f.write(f"  {escape_sql_string(row.password_hash)},\n")
                f.write(f"  {format_datetime(row.created_at)},\n")
                f.write(f"  {format_datetime(row.updated_at)}\n")
                f.write(");\n\n")
            
            # Export Property Suppliers
            print("[Export] Exporting property suppliers...")
            result = conn.execute(text("SELECT * FROM property_suppliers ORDER BY created_at"))
            ps = result.fetchall()
            f.write(f"-- Property Suppliers ({len(ps)} records)\n")
            for row in ps:
                f.write(f"INSERT INTO property_suppliers (id, property_id, supplier_id, credential_id, contract_id, direct_debit, created_at, updated_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.property_id)},\n")
                f.write(f"  {escape_sql_string(row.supplier_id)},\n")
                f.write(f"  {escape_sql_string(row.credential_id)},\n")
                f.write(f"  {escape_sql_string(row.contract_id)},\n")
                f.write(f"  {1 if row.direct_debit else 0},\n")
                f.write(f"  {format_datetime(row.created_at)},\n")
                f.write(f"  {format_datetime(row.updated_at)}\n")
                f.write(");\n\n")
            
            # Export User Preferences
            print("[Export] Exporting user preferences...")
            result = conn.execute(text("SELECT * FROM user_preferences ORDER BY user_id"))
            prefs = result.fetchall()
            f.write(f"-- User Preferences ({len(prefs)} records)\n")
            for row in prefs:
                f.write(f"INSERT INTO user_preferences (id, user_id, language, view_mode, rent_warning_days, "
                       f"rent_currency, bill_currency, date_format, phone_number, landlord_name, personal_email, iban, updated_at) VALUES (\n")
                f.write(f"  {escape_sql_string(row.id)},\n")
                f.write(f"  {escape_sql_string(row.user_id)},\n")
                f.write(f"  {escape_sql_string(row.language)},\n")
                f.write(f"  {escape_sql_string(row.view_mode)},\n")
                f.write(f"  {row.rent_warning_days if row.rent_warning_days is not None else 5},\n")
                f.write(f"  {escape_sql_string(row.rent_currency)},\n")
                f.write(f"  {escape_sql_string(row.bill_currency)},\n")
                f.write(f"  {escape_sql_string(row.date_format)},\n")
                f.write(f"  {escape_sql_string(row.phone_number)},\n")
                f.write(f"  {escape_sql_string(row.landlord_name)},\n")
                f.write(f"  {escape_sql_string(row.personal_email)},\n")
                f.write(f"  {escape_sql_string(row.iban)},\n")
                f.write(f"  {format_datetime(row.updated_at)}\n")
                f.write(");\n\n")
        
        f.write("-- Re-enable foreign key checks\n")
        f.write("PRAGMA foreign_keys = ON;\n\n")
        f.write("COMMIT;\n")
        f.write("\n-- Import complete!\n")
        f.write(f"-- Total tables: 9\n")
        f.write(f"-- Total records: {len(users) + len(properties) + len(renters) + len(suppliers) + len(bills) + len(payments) + len(creds) + len(ps) + len(prefs)}\n")
    
    print(f"\n✅ Data exported to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"  - Users: {len(users)}")
    print(f"  - Properties: {len(properties)}")
    print(f"  - Renters: {len(renters)}")
    print(f"  - Suppliers: {len(suppliers)}")
    print(f"  - Bills: {len(bills)}")
    print(f"  - Payments: {len(payments)}")
    print(f"  - Credentials: {len(creds)}")
    print(f"  - Property Suppliers: {len(ps)}")
    print(f"  - Preferences: {len(prefs)}")
    print(f"\n🚀 To import into SQLite:")
    print(f"  1. Create database: sqlite3 promanage.db < scripts/sqlite_typed_schema.sql")
    print(f"  2. Import data: sqlite3 promanage.db < scripts/sqlite_data_import.sql")
    print(f"  3. Update .env: DATABASE_URL=sqlite:///./promanage.db")
    print(f"  4. Restart backend")

if __name__ == '__main__':
    try:
        export_mysql_to_sqlite()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

