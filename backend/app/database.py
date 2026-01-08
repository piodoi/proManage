"""
Database abstraction layer - delegates to typed implementations
Supports both SQLite and MySQL with typed columns
"""

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Load .env file BEFORE reading environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.models import (
    User, Property, Renter, Bill, Payment,
    Supplier, PropertySupplier,
    UserPreferences, UserRole
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./promanage.db"
)

# Auto-detect database type
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_MYSQL = DATABASE_URL.startswith("mysql")
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")

# Enhanced logging
print("=" * 70)
print("[Database] DATABASE_URL Configuration:")
# Sanitize password for logging
safe_url = DATABASE_URL
if "@" in safe_url and "://" in safe_url:
    parts = safe_url.split("://")
    if len(parts) == 2 and "@" in parts[1]:
        creds, rest = parts[1].split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            safe_url = f"{parts[0]}://{user}:***@{rest}"
print(f"  URL: {safe_url}")
print(f"  Type: {'SQLite' if IS_SQLITE else 'MySQL' if IS_MYSQL else 'PostgreSQL' if IS_POSTGRESQL else 'Unknown'}")
print("=" * 70)

# Add +pymysql driver for MySQL if not already specified
if IS_MYSQL and '+pymysql' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('mysql://', 'mysql+pymysql://', 1)

# Initialize the appropriate typed database
_db_impl = None

if IS_MYSQL:
    from app.database_mysql import MySQLDatabase
    print("[Database] 🚀 Using MySQL with TYPED COLUMNS (relational model)")
    print("[Database] Features: Foreign keys, indexes, ENUM types, connection pooling")
    _db_impl = MySQLDatabase(DATABASE_URL)
    print("[Database] ✅ MySQL connection established!")
elif IS_SQLITE:
    from app.database_sqlite import SQLiteDatabase
    print("[Database] 🚀 Using SQLite with TYPED COLUMNS (relational model)")
    print("[Database] Features: Foreign keys, indexes, WAL mode, optimized queries")
    _db_impl = SQLiteDatabase(DATABASE_URL)
    print("[Database] ✅ SQLite connection established!")
else:
    raise ValueError(f"Unsupported database type: {DATABASE_URL}")


class Database:
    """
    Unified database interface - delegates all operations to typed implementations
    Works seamlessly with both SQLite and MySQL
    """
    
    def __init__(self):
        self._impl = _db_impl
        
        # Verify database schema
        if IS_MYSQL:
            try:
                from sqlalchemy import text
                with self._impl.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"))
                    table_count = result.fetchone()[0]
                    print(f"[Database] MySQL: {table_count} tables found")
                    if table_count == 0:
                        print("[Database] ⚠️  WARNING: No tables found!")
                        print("[Database] 💡 Run: mysql -u root -p ultrafinu_promanage < scripts/mysql_schema.sql")
                    elif table_count < 9:
                        print(f"[Database] ⚠️  WARNING: Only {table_count}/9 tables (incomplete schema?)")
                    else:
                        print(f"[Database] ✅ MySQL schema is ready!")
            except Exception as e:
                print(f"[Database] ❌ ERROR: {e}")
        elif IS_SQLITE:
            try:
                from sqlalchemy import text
                with self._impl.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
                    table_count = result.fetchone()[0]
                    print(f"[Database] SQLite: {table_count} tables found")
                    if table_count == 0:
                        print("[Database] ⚠️  WARNING: No tables found!")
                        print("[Database] 💡 Run: sqlite3 promanage.db < scripts/sqlite_typed_schema.sql")
                    else:
                        print(f"[Database] ✅ SQLite schema is ready!")
            except Exception as e:
                print(f"[Database] ⚠️  Schema check: {e}")
    
    # ==================== USER OPERATIONS ====================
    def get_user(self, user_id: str) -> Optional[User]:
        return self._impl.get_user_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self._impl.get_user_by_email(email)
    
    def list_users(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[User]:
        # Temporary implementation using raw SQL
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            query = "SELECT * FROM users"
            if limit is not None and offset is not None:
                query += f" LIMIT {offset}, {limit}"
            elif limit is not None:
                query += f" LIMIT {limit}"
            result = conn.execute(text(query))
            users = []
            for row in result:
                users.append(User(
                    id=row.id,
                    email=row.email,
                    name=row.name,
                    role=row.role,
                    password_hash=row.password_hash,
                    oauth_provider=row.oauth_provider,
                    oauth_id=row.oauth_id,
                    subscription_tier=row.subscription_tier,
                    subscription_expires=row.subscription_expires.isoformat() if row.subscription_expires and hasattr(row.subscription_expires, 'isoformat') else row.subscription_expires,
                    created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                ))
            return users
    
    def count_users(self) -> int:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()
            return result[0] if result else 0
    
    def save_user(self, user: User) -> User:
        existing = self._impl.get_user_by_id(user.id)
        if existing:
            updates = {}
            for field in ['email', 'name', 'password_hash', 'subscription_tier', 'subscription_expires']:
                if getattr(user, field, None) != getattr(existing, field, None):
                    updates[field] = getattr(user, field)
            if updates:
                return self._impl.update_user(user.id, updates)
            return existing
        else:
            return self._impl.create_user(user)
    
    def delete_user(self, user_id: str) -> bool:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            conn.commit()
            return result.rowcount > 0
    
    # ==================== PROPERTY OPERATIONS ====================
    def get_property(self, property_id: str) -> Optional[Property]:
        return self._impl.get_property_by_id(property_id)
    
    def list_properties(self, landlord_id: Optional[str] = None) -> List[Property]:
        if landlord_id:
            return self._impl.get_properties_by_landlord(landlord_id)
        else:
            from sqlalchemy import text
            with self._impl.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM properties ORDER BY created_at DESC"))
                properties = []
                for row in result:
                    properties.append(Property(
                        id=row.id,
                        landlord_id=row.landlord_id,
                        address=row.address,
                        name=row.name,
                        created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                    ))
                return properties
    
    def count_properties(self, landlord_id: str) -> int:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM properties WHERE landlord_id = :lid"),
                {"lid": landlord_id}
            ).fetchone()
            return result[0] if result else 0
    
    def save_property(self, prop: Property) -> Property:
        existing = self._impl.get_property_by_id(prop.id)
        if existing:
            updates = {}
            for field in ['address', 'name']:
                if getattr(prop, field) != getattr(existing, field):
                    updates[field] = getattr(prop, field)
            if updates:
                return self._impl.update_property(prop.id, updates)
            return existing
        else:
            return self._impl.create_property(prop)
    
    def delete_property(self, property_id: str) -> bool:
        return self._impl.delete_property(property_id)
    
    # ==================== RENTER OPERATIONS ====================
    def get_renter(self, renter_id: str) -> Optional[Renter]:
        return self._impl.get_renter_by_id(renter_id)
    
    def get_renter_by_token(self, token: str) -> Optional[Renter]:
        return self._impl.get_renter_by_token(token)
    
    def list_renters(self, property_id: Optional[str] = None) -> List[Renter]:
        if property_id:
            return self._impl.get_renters_by_property(property_id)
        else:
            from sqlalchemy import text
            with self._impl.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM renters ORDER BY name"))
                renters = []
                for row in result:
                    renters.append(Renter(
                        id=row.id,
                        property_id=row.property_id,
                        name=row.name,
                        email=row.email,
                        phone=row.phone,
                        rent_day=row.rent_day,
                        start_contract_date=row.start_contract_date if isinstance(row.start_contract_date, str) else (row.start_contract_date.isoformat() if row.start_contract_date else None),
                        rent_amount_eur=float(row.rent_amount_eur) if row.rent_amount_eur else None,
                        access_token=row.access_token,
                        created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                    ))
                return renters
    
    def save_renter(self, renter: Renter) -> Renter:
        existing = self._impl.get_renter_by_id(renter.id)
        if existing:
            updates = {}
            for field in ['name', 'email', 'phone', 'rent_day', 'start_contract_date', 'rent_amount_eur']:
                if getattr(renter, field) != getattr(existing, field):
                    updates[field] = getattr(renter, field)
            if updates:
                return self._impl.update_renter(renter.id, updates)
            return existing
        else:
            return self._impl.create_renter(renter)
    
    def delete_renter(self, renter_id: str) -> bool:
        return self._impl.delete_renter(renter_id)
    
    # ==================== BILL OPERATIONS ====================
    def get_bill(self, bill_id: str) -> Optional[Bill]:
        return self._impl.get_bill_by_id(bill_id)
    
    def list_bills(self, property_id: Optional[str] = None, renter_id: Optional[str] = None) -> List[Bill]:
        if property_id:
            return self._impl.get_bills_by_property(property_id, renter_id)
        else:
            from sqlalchemy import text
            with self._impl.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM bills ORDER BY due_date DESC"))
                bills = []
                for row in result:
                    bills.append(self._impl._row_to_bill(row))
                return bills
    
    def save_bill(self, bill: Bill) -> Bill:
        existing = self._impl.get_bill_by_id(bill.id)
        if existing:
            updates = {}
            for field in ['description', 'amount', 'currency', 'due_date', 'bill_date', 
                         'legal_name', 'iban', 'bill_number', 'status', 'supplier_id',
                         'extraction_pattern_id', 'contract_id', 'payment_details', 'renter_id']:
                if getattr(bill, field) != getattr(existing, field):
                    updates[field] = getattr(bill, field)
            if updates:
                return self._impl.update_bill(bill.id, updates)
            return existing
        else:
            return self._impl.create_bill(bill)
    
    def delete_bill(self, bill_id: str) -> bool:
        return self._impl.delete_bill(bill_id)
    
    # ==================== PAYMENT OPERATIONS ====================
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM payments WHERE id = :id"), {"id": payment_id})
            row = result.fetchone()
            if row:
                return Payment(
                    id=row.id,
                    bill_id=row.bill_id,
                    amount=float(row.amount),
                    method=row.method,
                    status=row.status,
                    commission=float(row.commission) if row.commission else 0,
                    created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                )
            return None
    
    def list_payments(self, bill_id: Optional[str] = None) -> List[Payment]:
        if bill_id:
            return self._impl.get_payments_by_bill(bill_id)
        else:
            from sqlalchemy import text
            with self._impl.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM payments ORDER BY created_at DESC"))
                payments = []
                for row in result:
                    payments.append(Payment(
                        id=row.id,
                        bill_id=row.bill_id,
                        amount=float(row.amount),
                        method=row.method,
                        status=row.status,
                        commission=float(row.commission) if row.commission else 0,
                        created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                    ))
                return payments
    
    def list_payments_for_bills(self, bill_ids: List[str]) -> List[Payment]:
        if not bill_ids:
            return []
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            placeholders = ', '.join([f"'{bid}'" for bid in bill_ids])
            query = f"SELECT * FROM payments WHERE bill_id IN ({placeholders})"
            result = conn.execute(text(query))
            payments = []
            for row in result:
                payments.append(Payment(
                    id=row.id,
                    bill_id=row.bill_id,
                    amount=float(row.amount),
                    method=row.method,
                    status=row.status,
                    commission=float(row.commission) if row.commission else 0,
                    created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None)
                ))
            return payments
    
    def save_payment(self, payment: Payment) -> Payment:
        return self._impl.create_payment(payment)
    
    # ==================== SUPPLIER OPERATIONS ====================
    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        return self._impl.get_supplier_by_id(supplier_id)
    
    def get_supplier_by_name(self, name: str) -> Optional[Supplier]:
        all_suppliers = self._impl.get_all_suppliers()
        for s in all_suppliers:
            if s.name == name:
                return s
        return None
    
    def list_suppliers(self) -> List[Supplier]:
        return self._impl.get_all_suppliers()
    
    def save_supplier(self, supplier: Supplier) -> Supplier:
        # Check if supplier exists to determine create vs update
        existing = self._impl.get_supplier_by_id(supplier.id)
        if existing:
            return self._impl.update_supplier(supplier)
        else:
            return self._impl.create_supplier(supplier)
    
    def delete_supplier(self, supplier_id: str) -> bool:
        return self._impl.delete_supplier(supplier_id)
    
    # ==================== PROPERTY SUPPLIERS ====================
    def get_property_supplier(self, property_supplier_id: str) -> Optional[PropertySupplier]:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM property_suppliers WHERE id = :id"),
                {"id": property_supplier_id}
            )
            row = result.fetchone()
            if row:
                return PropertySupplier(
                    id=row.id,
                    property_id=row.property_id,
                    supplier_id=row.supplier_id,
                    credential_id=row.credential_id,
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None),
                    updated_at=row.updated_at if isinstance(row.updated_at, str) else (row.updated_at.isoformat() if row.updated_at else None)
                )
            return None
    
    def list_property_suppliers(self, property_id: str) -> List[PropertySupplier]:
        return self._impl.get_property_suppliers(property_id)
    
    def get_property_supplier_by_supplier(self, property_id: str, supplier_id: str) -> Optional[PropertySupplier]:
        return self._impl.get_property_supplier(property_id, supplier_id)
    
    def get_property_supplier_by_supplier_and_contract(self, property_id: str, supplier_id: str, contract_id: Optional[str]) -> Optional[PropertySupplier]:
        suppliers = self._impl.get_property_suppliers(property_id)
        for ps in suppliers:
            if ps.supplier_id == supplier_id:
                if (not contract_id and not ps.contract_id) or (contract_id == ps.contract_id):
                    return ps
        return None
    
    def save_property_supplier(self, property_supplier: PropertySupplier) -> PropertySupplier:
        existing = self._impl.get_property_supplier(property_supplier.property_id, property_supplier.supplier_id)
        if existing:
            updates = {}
            for field in ['credential_id', 'contract_id', 'direct_debit']:
                if getattr(property_supplier, field) != getattr(existing, field):
                    updates[field] = getattr(property_supplier, field)
            if updates:
                return self._impl.update_property_supplier(existing.id, updates)
            return existing
        else:
            return self._impl.create_property_supplier(property_supplier)
    
    def delete_property_supplier(self, property_supplier_id: str) -> bool:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(
                text("DELETE FROM property_suppliers WHERE id = :id"),
                {"id": property_supplier_id}
            )
            conn.commit()
            return result.rowcount > 0
    
    def list_property_suppliers_by_supplier(self, supplier_id: str) -> List[PropertySupplier]:
        from sqlalchemy import text
        with self._impl.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM property_suppliers WHERE supplier_id = :supplier_id"),
                {"supplier_id": supplier_id}
            )
            suppliers = []
            for row in result:
                suppliers.append(PropertySupplier(
                    id=row.id,
                    property_id=row.property_id,
                    supplier_id=row.supplier_id,
                    credential_id=row.credential_id,
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at if isinstance(row.created_at, str) else (row.created_at.isoformat() if row.created_at else None),
                    updated_at=row.updated_at if isinstance(row.updated_at, str) else (row.updated_at.isoformat() if row.updated_at else None)
                ))
            return suppliers
    
    # ==================== USER SUPPLIER CREDENTIALS ====================
    # ==================== USER PREFERENCES ====================
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        return self._impl.get_user_preferences(user_id)
    
    def save_user_preferences(self, preferences: UserPreferences) -> UserPreferences:
        from datetime import datetime
        preferences.updated_at = datetime.utcnow()
        return self._impl.create_user_preferences(preferences)


# Create global database instance
db = Database()


def has_any_admin() -> bool:
    """Check if any admin user exists in the database."""
    users = db.list_users()
    return any(u.role == UserRole.ADMIN for u in users)
