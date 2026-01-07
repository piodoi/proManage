import os
from typing import Optional, TypeVar, Type
from sqlalchemy import create_engine, Column, String, Text, Integer, MetaData, Table, text, func
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel

# Load .env file BEFORE reading environment variables
from dotenv import load_dotenv
from pathlib import Path

# Find and load .env from backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.models import (
    User, Property, Renter, Bill, Payment,
    ExtractionPattern, UserRole, Supplier, PropertySupplier, UserSupplierCredential,
    UserPreferences
)

T = TypeVar("T", bound=BaseModel)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./promanage.db"
)

# Auto-detect database type and log for clarity
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_MYSQL = DATABASE_URL.startswith("mysql")
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")

# Enhanced logging to show database configuration
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
    print("[Database] ✓ Added +pymysql driver to MySQL URL")

# Use MySQL typed-column database if MySQL is detected
if IS_MYSQL:
    from app.database_mysql import MySQLDatabase
    print("[Database] 🚀 Using MySQL with TYPED COLUMNS (relational model)")
    print("[Database] Features: Foreign keys, indexes, ENUM types, connection pooling")
    _mysql_db = MySQLDatabase(DATABASE_URL)
    print("[Database] ✅ MySQL connection established!")
else:
    _mysql_db = None
    print("[Database] 📝 Using SQLite with DOCUMENT MODEL (JSON storage)")

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # Wait up to 30 seconds for locks to clear
        },
        pool_pre_ping=True,
        poolclass=QueuePool,  # Use connection pooling even for SQLite
        pool_size=1,  # Single connection for SQLite to prevent corruption
        max_overflow=0,  # No overflow connections
        echo=False,  # Set to True for SQL debugging
    )
    
    # Enable WAL mode for better concurrency and data safety
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
        cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.close()
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

metadata = MetaData()

users_table = Table(
    "users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), index=True),
    Column("data", Text, nullable=False),
)

properties_table = Table(
    "properties", metadata,
    Column("id", String(36), primary_key=True),
    Column("landlord_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

renters_table = Table(
    "renters", metadata,
    Column("id", String(36), primary_key=True),
    Column("property_id", String(36), index=True),
    Column("access_token", String(36), index=True),
    Column("data", Text, nullable=False),
)

bills_table = Table(
    "bills", metadata,
    Column("id", String(36), primary_key=True),
    Column("property_id", String(36), index=True),
    Column("renter_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

payments_table = Table(
    "payments", metadata,
    Column("id", String(36), primary_key=True),
    Column("bill_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

extraction_patterns_table = Table(
    "extraction_patterns", metadata,
    Column("id", String(36), primary_key=True),
    Column("priority", Integer, index=True),
    Column("data", Text, nullable=False),
)

suppliers_table = Table(
    "suppliers", metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(255), index=True),
    Column("data", Text, nullable=False),
)

user_supplier_credentials_table = Table(
    "user_supplier_credentials", metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), index=True),
    Column("supplier_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

property_suppliers_table = Table(
    "property_suppliers", metadata,
    Column("id", String(36), primary_key=True),
    Column("property_id", String(36), index=True),
    Column("supplier_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

user_preferences_table = Table(
    "user_preferences", metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), index=True, unique=True),
    Column("data", Text, nullable=False),
)


def _serialize(obj: BaseModel) -> str:
    return obj.model_dump_json()


def _deserialize(model_class: Type[T], data: str) -> T:
    return model_class.model_validate_json(data)


class Database:
    def __init__(self):
        # For MySQL, schema is created by migration script
        # For SQLite, create tables automatically
        if IS_SQLITE:
            metadata.create_all(engine)
            # Count tables
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
                    table_count = result.fetchone()[0]
                    print(f"[Database] SQLite: {table_count} tables initialized")
            except Exception as e:
                print(f"[Database] SQLite table check failed: {e}")
        elif IS_MYSQL:
            # Verify MySQL connection and tables
            try:
                with _mysql_db.engine.connect() as conn:
                    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"))
                    table_count = result.fetchone()[0]
                    print(f"[Database] MySQL: {table_count} tables found in database")
                    if table_count == 0:
                        print("[Database] ⚠️  WARNING: No tables found!")
                        print("[Database] 💡 Run: mysql -u root -p ultrafinu_promanage < scripts/mysql_schema.sql")
                        print("[Database] 💡 Then: mysql -u root -p ultrafinu_promanage < scripts/mysql_data_import.sql")
                    elif table_count < 10:
                        print(f"[Database] ⚠️  WARNING: Only {table_count}/10 tables (incomplete schema?)")
                    else:
                        print(f"[Database] ✅ MySQL schema is ready!")
            except Exception as e:
                print(f"[Database] ❌ ERROR: MySQL connection/query failed: {e}")
                print("[Database] 💡 Check: Is MySQL server running? Does database exist?")
                print("[Database] 💡 Create DB: mysql -u root -p -e 'CREATE DATABASE ultrafinu_promanage'")
        
        # Store reference to MySQL database if using MySQL
        self._mysql_db = _mysql_db if IS_MYSQL else None

    def get_user(self, user_id: str) -> Optional[User]:
        if self._mysql_db:
            return self._mysql_db.get_user_by_id(user_id)
        with engine.connect() as conn:
            result = conn.execute(
                users_table.select().where(users_table.c.id == user_id)
            ).fetchone()
            return _deserialize(User, result.data) if result else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        if self._mysql_db:
            return self._mysql_db.get_user_by_email(email)
        with engine.connect() as conn:
            result = conn.execute(
                users_table.select().where(users_table.c.email == email)
            ).fetchone()
            return _deserialize(User, result.data) if result else None

    def list_users(self, limit: Optional[int] = None, offset: Optional[int] = None) -> list[User]:
        if self._mysql_db:
            # MySQL: Use raw SQL to get all users with limit/offset
            with self._mysql_db.engine.connect() as conn:
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
                        subscription_expires=row.subscription_expires.isoformat() if row.subscription_expires else None,
                        ebloc_username=row.ebloc_username,
                        ebloc_password_hash=row.ebloc_password_hash,
                        created_at=row.created_at.isoformat() if row.created_at else None
                    ))
                return users
        with engine.connect() as conn:
            query = users_table.select()
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)
            results = conn.execute(query).fetchall()
            return [_deserialize(User, r.data) for r in results]
    
    def count_users(self) -> int:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()
            return result[0] if result else 0

    def save_user(self, user: User) -> User:
        if self._mysql_db:
            existing = self._mysql_db.get_user_by_id(user.id)
            if existing:
                # Update user - extract changed fields
                updates = {}
                if user.email != existing.email:
                    updates['email'] = user.email
                if user.name != existing.name:
                    updates['name'] = user.name
                if user.password_hash != existing.password_hash:
                    updates['password_hash'] = user.password_hash
                if user.ebloc_username != existing.ebloc_username:
                    updates['ebloc_username'] = user.ebloc_username
                if user.ebloc_password_hash != existing.ebloc_password_hash:
                    updates['ebloc_password_hash'] = user.ebloc_password_hash
                if updates:
                    return self._mysql_db.update_user(user.id, updates)
                return existing
            else:
                return self._mysql_db.create_user(user)
        with engine.connect() as conn:
            existing = conn.execute(
                users_table.select().where(users_table.c.id == user.id)
            ).fetchone()
            if existing:
                conn.execute(
                    users_table.update().where(users_table.c.id == user.id).values(
                        email=user.email, data=_serialize(user)
                    )
                )
            else:
                conn.execute(
                    users_table.insert().values(
                        id=user.id, email=user.email, data=_serialize(user)
                    )
                )
            conn.commit()
        return user

    def delete_user(self, user_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                users_table.delete().where(users_table.c.id == user_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_property(self, property_id: str) -> Optional[Property]:
        if self._mysql_db:
            return self._mysql_db.get_property_by_id(property_id)
        with engine.connect() as conn:
            result = conn.execute(
                properties_table.select().where(properties_table.c.id == property_id)
            ).fetchone()
            return _deserialize(Property, result.data) if result else None

    def list_properties(self, landlord_id: Optional[str] = None) -> list[Property]:
        if self._mysql_db:
            if landlord_id:
                return self._mysql_db.get_properties_by_landlord(landlord_id)
            else:
                # Get all properties
                with self._mysql_db.engine.connect() as conn:
                    result = conn.execute(text("SELECT * FROM properties ORDER BY created_at DESC"))
                    properties = []
                    for row in result:
                        properties.append(Property(
                            id=row.id,
                            landlord_id=row.landlord_id,
                            address=row.address,
                            name=row.name,
                            created_at=row.created_at.isoformat() if row.created_at else None
                        ))
                    return properties
        with engine.connect() as conn:
            if landlord_id:
                results = conn.execute(
                    properties_table.select().where(properties_table.c.landlord_id == landlord_id)
                ).fetchall()
            else:
                results = conn.execute(properties_table.select()).fetchall()
            return [_deserialize(Property, r.data) for r in results]

    def save_property(self, prop: Property) -> Property:
        if self._mysql_db:
            existing = self._mysql_db.get_property_by_id(prop.id)
            if existing:
                updates = {}
                if prop.address != existing.address:
                    updates['address'] = prop.address
                if prop.name != existing.name:
                    updates['name'] = prop.name
                if updates:
                    return self._mysql_db.update_property(prop.id, updates)
                return existing
            else:
                return self._mysql_db.create_property(prop)
        with engine.connect() as conn:
            existing = conn.execute(
                properties_table.select().where(properties_table.c.id == prop.id)
            ).fetchone()
            if existing:
                conn.execute(
                    properties_table.update().where(properties_table.c.id == prop.id).values(
                        landlord_id=prop.landlord_id, data=_serialize(prop)
                    )
                )
            else:
                conn.execute(
                    properties_table.insert().values(
                        id=prop.id, landlord_id=prop.landlord_id, data=_serialize(prop)
                    )
                )
            conn.commit()
        return prop

    def delete_property(self, property_id: str) -> bool:
        if self._mysql_db:
            return self._mysql_db.delete_property(property_id)
        with engine.connect() as conn:
            result = conn.execute(
                properties_table.delete().where(properties_table.c.id == property_id)
            )
            conn.commit()
            return result.rowcount > 0

    def count_properties(self, landlord_id: str) -> int:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM properties WHERE landlord_id = :lid"),
                {"lid": landlord_id}
            ).fetchone()
            return result[0] if result else 0

    def get_renter(self, renter_id: str) -> Optional[Renter]:
        if self._mysql_db:
            return self._mysql_db.get_renter_by_id(renter_id)
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.select().where(renters_table.c.id == renter_id)
            ).fetchone()
            return _deserialize(Renter, result.data) if result else None

    def get_renter_by_token(self, token: str) -> Optional[Renter]:
        if self._mysql_db:
            return self._mysql_db.get_renter_by_token(token)
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.select().where(renters_table.c.access_token == token)
            ).fetchone()
            return _deserialize(Renter, result.data) if result else None

    def list_renters(self, property_id: Optional[str] = None) -> list[Renter]:
        if self._mysql_db:
            if property_id:
                return self._mysql_db.get_renters_by_property(property_id)
            else:
                # Get all renters
                with self._mysql_db.engine.connect() as conn:
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
                            start_contract_date=row.start_contract_date.isoformat() if row.start_contract_date else None,
                            rent_amount_eur=float(row.rent_amount_eur) if row.rent_amount_eur else None,
                            access_token=row.access_token,
                            created_at=row.created_at.isoformat() if row.created_at else None
                        ))
                    return renters
        with engine.connect() as conn:
            if property_id:
                results = conn.execute(
                    renters_table.select().where(renters_table.c.property_id == property_id)
                ).fetchall()
            else:
                results = conn.execute(renters_table.select()).fetchall()
            return [_deserialize(Renter, r.data) for r in results]

    def save_renter(self, renter: Renter) -> Renter:
        if self._mysql_db:
            existing = self._mysql_db.get_renter_by_id(renter.id)
            if existing:
                updates = {}
                for field in ['name', 'email', 'phone', 'rent_day', 'start_contract_date', 'rent_amount_eur']:
                    if getattr(renter, field) != getattr(existing, field):
                        updates[field] = getattr(renter, field)
                if updates:
                    return self._mysql_db.update_renter(renter.id, updates)
                return existing
            else:
                return self._mysql_db.create_renter(renter)
        with engine.connect() as conn:
            existing = conn.execute(
                renters_table.select().where(renters_table.c.id == renter.id)
            ).fetchone()
            if existing:
                conn.execute(
                    renters_table.update().where(renters_table.c.id == renter.id).values(
                        property_id=renter.property_id, access_token=renter.access_token, data=_serialize(renter)
                    )
                )
            else:
                conn.execute(
                    renters_table.insert().values(
                        id=renter.id, property_id=renter.property_id,
                        access_token=renter.access_token, data=_serialize(renter)
                    )
                )
            conn.commit()
        return renter

    def delete_renter(self, renter_id: str) -> bool:
        if self._mysql_db:
            return self._mysql_db.delete_renter(renter_id)
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.delete().where(renters_table.c.id == renter_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        if self._mysql_db:
            return self._mysql_db.get_bill_by_id(bill_id)
        with engine.connect() as conn:
            result = conn.execute(
                bills_table.select().where(bills_table.c.id == bill_id)
            ).fetchone()
            return _deserialize(Bill, result.data) if result else None

    def list_bills(self, property_id: Optional[str] = None, renter_id: Optional[str] = None) -> list[Bill]:
        if self._mysql_db:
            if property_id:
                return self._mysql_db.get_bills_by_property(property_id, renter_id)
            else:
                # Get all bills - use raw SQL
                with self._mysql_db.engine.connect() as conn:
                    query = "SELECT * FROM bills ORDER BY due_date DESC"
                    result = conn.execute(text(query))
                    bills = []
                    for row in result:
                        bills.append(self._mysql_db._row_to_bill(row))
                    return bills
        with engine.connect() as conn:
            query = bills_table.select()
            if property_id:
                query = query.where(bills_table.c.property_id == property_id)
            if renter_id:
                query = query.where(bills_table.c.renter_id == renter_id)
            results = conn.execute(query).fetchall()
            return [_deserialize(Bill, r.data) for r in results]

    def save_bill(self, bill: Bill) -> Bill:
        if self._mysql_db:
            existing = self._mysql_db.get_bill_by_id(bill.id)
            if existing:
                updates = {}
                for field in ['description', 'amount', 'currency', 'due_date', 'bill_date', 
                             'legal_name', 'iban', 'bill_number', 'status', 'supplier_id',
                             'extraction_pattern_id', 'contract_id', 'payment_details', 'renter_id']:
                    if getattr(bill, field) != getattr(existing, field):
                        updates[field] = getattr(bill, field)
                if updates:
                    return self._mysql_db.update_bill(bill.id, updates)
                return existing
            else:
                return self._mysql_db.create_bill(bill)
        with engine.connect() as conn:
            existing = conn.execute(
                bills_table.select().where(bills_table.c.id == bill.id)
            ).fetchone()
            if existing:
                conn.execute(
                    bills_table.update().where(bills_table.c.id == bill.id).values(
                        property_id=bill.property_id, renter_id=bill.renter_id, data=_serialize(bill)
                    )
                )
            else:
                conn.execute(
                    bills_table.insert().values(
                        id=bill.id, property_id=bill.property_id, renter_id=bill.renter_id, data=_serialize(bill)
                    )
                )
            conn.commit()
        return bill

    def delete_bill(self, bill_id: str) -> bool:
        if self._mysql_db:
            return self._mysql_db.delete_bill(bill_id)
        with engine.connect() as conn:
            result = conn.execute(
                bills_table.delete().where(bills_table.c.id == bill_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        with engine.connect() as conn:
            result = conn.execute(
                payments_table.select().where(payments_table.c.id == payment_id)
            ).fetchone()
            return _deserialize(Payment, result.data) if result else None

    def list_payments(self, bill_id: Optional[str] = None) -> list[Payment]:
        if self._mysql_db:
            if bill_id:
                return self._mysql_db.get_payments_by_bill(bill_id)
            else:
                # Get all payments
                with self._mysql_db.engine.connect() as conn:
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
                            created_at=row.created_at.isoformat() if row.created_at else None
                        ))
                    return payments
        with engine.connect() as conn:
            if bill_id:
                results = conn.execute(
                    payments_table.select().where(payments_table.c.bill_id == bill_id)
                ).fetchall()
            else:
                results = conn.execute(payments_table.select()).fetchall()
            return [_deserialize(Payment, r.data) for r in results]

    def list_payments_for_bills(self, bill_ids: list[str]) -> list[Payment]:
        """Fetch all payments for multiple bills at once (avoids N+1 queries)."""
        if not bill_ids:
            return []
        if self._mysql_db:
            with self._mysql_db.engine.connect() as conn:
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
                        created_at=row.created_at.isoformat() if row.created_at else None
                    ))
                return payments
        with engine.connect() as conn:
            results = conn.execute(
                payments_table.select().where(payments_table.c.bill_id.in_(bill_ids))
            ).fetchall()
            return [_deserialize(Payment, r.data) for r in results]

    def save_payment(self, payment: Payment) -> Payment:
        with engine.connect() as conn:
            existing = conn.execute(
                payments_table.select().where(payments_table.c.id == payment.id)
            ).fetchone()
            if existing:
                conn.execute(
                    payments_table.update().where(payments_table.c.id == payment.id).values(
                        bill_id=payment.bill_id, data=_serialize(payment)
                    )
                )
            else:
                conn.execute(
                    payments_table.insert().values(
                        id=payment.id, bill_id=payment.bill_id, data=_serialize(payment)
                    )
                )
            conn.commit()
        return payment

    def get_extraction_pattern(self, pattern_id: str) -> Optional[ExtractionPattern]:
        with engine.connect() as conn:
            result = conn.execute(
                extraction_patterns_table.select().where(extraction_patterns_table.c.id == pattern_id)
            ).fetchone()
            return _deserialize(ExtractionPattern, result.data) if result else None

    def list_extraction_patterns(self) -> list[ExtractionPattern]:
        with engine.connect() as conn:
            results = conn.execute(
                extraction_patterns_table.select().order_by(extraction_patterns_table.c.priority.desc())
            ).fetchall()
            return [_deserialize(ExtractionPattern, r.data) for r in results]

    def save_extraction_pattern(self, pattern: ExtractionPattern) -> ExtractionPattern:
        with engine.connect() as conn:
            existing = conn.execute(
                extraction_patterns_table.select().where(extraction_patterns_table.c.id == pattern.id)
            ).fetchone()
            if existing:
                conn.execute(
                    extraction_patterns_table.update().where(extraction_patterns_table.c.id == pattern.id).values(
                        priority=pattern.priority, data=_serialize(pattern)
                    )
                )
            else:
                conn.execute(
                    extraction_patterns_table.insert().values(
                        id=pattern.id, priority=pattern.priority, data=_serialize(pattern)
                    )
                )
            conn.commit()
        return pattern

    def delete_extraction_pattern(self, pattern_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                extraction_patterns_table.delete().where(extraction_patterns_table.c.id == pattern_id)
            )
            conn.commit()
            return result.rowcount > 0

    # Supplier methods
    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        if self._mysql_db:
            return self._mysql_db.get_supplier_by_id(supplier_id)
        with engine.connect() as conn:
            result = conn.execute(
                suppliers_table.select().where(suppliers_table.c.id == supplier_id)
            ).fetchone()
            return _deserialize(Supplier, result.data) if result else None

    def get_supplier_by_name(self, name: str) -> Optional[Supplier]:
        # MySQL doesn't have this method yet, fallback to listing and searching
        if self._mysql_db:
            all_suppliers = self._mysql_db.get_all_suppliers()
            for s in all_suppliers:
                if s.name == name:
                    return s
            return None
        with engine.connect() as conn:
            result = conn.execute(
                suppliers_table.select().where(suppliers_table.c.name == name)
            ).fetchone()
            return _deserialize(Supplier, result.data) if result else None

    def list_suppliers(self) -> list[Supplier]:
        if self._mysql_db:
            return self._mysql_db.get_all_suppliers()
        with engine.connect() as conn:
            results = conn.execute(suppliers_table.select()).fetchall()
            return [_deserialize(Supplier, r.data) for r in results]

    def save_supplier(self, supplier: Supplier) -> Supplier:
        if self._mysql_db:
            return self._mysql_db.create_supplier(supplier)
        with engine.connect() as conn:
            existing = conn.execute(
                suppliers_table.select().where(suppliers_table.c.id == supplier.id)
            ).fetchone()
            if existing:
                conn.execute(
                    suppliers_table.update().where(suppliers_table.c.id == supplier.id).values(
                        name=supplier.name, data=_serialize(supplier)
                    )
                )
            else:
                conn.execute(
                    suppliers_table.insert().values(
                        id=supplier.id, name=supplier.name, data=_serialize(supplier)
                    )
                )
            conn.commit()
        return supplier

    def delete_supplier(self, supplier_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                suppliers_table.delete().where(suppliers_table.c.id == supplier_id)
            )
            conn.commit()
            return result.rowcount > 0

    # PropertySupplier methods
    def get_property_supplier(self, property_supplier_id: str) -> Optional[PropertySupplier]:
        if self._mysql_db:
            # Get by ID - need to query directly
            with self._mysql_db.engine.connect() as conn:
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
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        updated_at=row.updated_at.isoformat() if row.updated_at else None
                    )
                return None
        with engine.connect() as conn:
            result = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.id == property_supplier_id)
            ).fetchone()
            return _deserialize(PropertySupplier, result.data) if result else None

    def list_property_suppliers(self, property_id: str) -> list[PropertySupplier]:
        if self._mysql_db:
            return self._mysql_db.get_property_suppliers(property_id)
        with engine.connect() as conn:
            results = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.property_id == property_id)
            ).fetchall()
            return [_deserialize(PropertySupplier, r.data) for r in results]

    def get_property_supplier_by_supplier(self, property_id: str, supplier_id: str) -> Optional[PropertySupplier]:
        if self._mysql_db:
            return self._mysql_db.get_property_supplier(property_id, supplier_id)
        with engine.connect() as conn:
            result = conn.execute(
                property_suppliers_table.select().where(
                    (property_suppliers_table.c.property_id == property_id) &
                    (property_suppliers_table.c.supplier_id == supplier_id)
                )
            ).fetchone()
            return _deserialize(PropertySupplier, result.data) if result else None
    
    def get_property_supplier_by_supplier_and_contract(self, property_id: str, supplier_id: str, contract_id: Optional[str]) -> Optional[PropertySupplier]:
        """Get property supplier by supplier_id and contract_id (to check for exact duplicates)"""
        if self._mysql_db:
            # For MySQL, get property_suppliers for property and check contract_id match
            suppliers = self._mysql_db.get_property_suppliers(property_id)
            for ps in suppliers:
                if ps.supplier_id == supplier_id:
                    # Both None or both equal
                    if (not contract_id and not ps.contract_id) or (contract_id == ps.contract_id):
                        return ps
            return None
        with engine.connect() as conn:
            # Get all property suppliers for this property and supplier
            results = conn.execute(
                property_suppliers_table.select().where(
                    (property_suppliers_table.c.property_id == property_id) &
                    (property_suppliers_table.c.supplier_id == supplier_id)
                )
            ).fetchall()
            
            # Check if any match the contract_id (handling None case)
            for row in results:
                ps = _deserialize(PropertySupplier, row.data)
                # Both None or both equal
                if (not contract_id and not ps.contract_id) or (contract_id == ps.contract_id):
                    return ps
            return None

    def save_property_supplier(self, property_supplier: PropertySupplier) -> PropertySupplier:
        if self._mysql_db:
            existing = self._mysql_db.get_property_supplier(property_supplier.property_id, property_supplier.supplier_id)
            if existing:
                updates = {}
                for field in ['credential_id', 'contract_id', 'direct_debit']:
                    if getattr(property_supplier, field) != getattr(existing, field):
                        updates[field] = getattr(property_supplier, field)
                if updates:
                    return self._mysql_db.update_property_supplier(existing.id, updates)
                return existing
            else:
                return self._mysql_db.create_property_supplier(property_supplier)
        with engine.connect() as conn:
            existing = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.id == property_supplier.id)
            ).fetchone()
            if existing:
                conn.execute(
                    property_suppliers_table.update().where(property_suppliers_table.c.id == property_supplier.id).values(
                        property_id=property_supplier.property_id,
                        supplier_id=property_supplier.supplier_id,
                        data=_serialize(property_supplier)
                    )
                )
            else:
                conn.execute(
                    property_suppliers_table.insert().values(
                        id=property_supplier.id,
                        property_id=property_supplier.property_id,
                        supplier_id=property_supplier.supplier_id,
                        data=_serialize(property_supplier)
                    )
                )
            conn.commit()
        return property_supplier

    def delete_property_supplier(self, property_supplier_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                property_suppliers_table.delete().where(property_suppliers_table.c.id == property_supplier_id)
            )
            conn.commit()
            return result.rowcount > 0
    
    def list_property_suppliers_by_supplier(self, supplier_id: str) -> list[PropertySupplier]:
        """Get all property-supplier relationships for a given supplier"""
        if self._mysql_db:
            with self._mysql_db.engine.connect() as conn:
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
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        updated_at=row.updated_at.isoformat() if row.updated_at else None
                    ))
                return suppliers
        with engine.connect() as conn:
            results = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.supplier_id == supplier_id)
            ).fetchall()
            return [_deserialize(PropertySupplier, r.data) for r in results]

    # UserSupplierCredential methods
    def get_user_supplier_credential(self, credential_id: str) -> Optional[UserSupplierCredential]:
        if self._mysql_db:
            with self._mysql_db.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM user_supplier_credentials WHERE id = :id"),
                    {"id": credential_id}
                )
                row = result.fetchone()
                if row:
                    return UserSupplierCredential(
                        id=row.id,
                        user_id=row.user_id,
                        supplier_id=row.supplier_id,
                        username=row.username,
                        password_hash=row.password_hash,
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        updated_at=row.updated_at.isoformat() if row.updated_at else None
                    )
                return None
        with engine.connect() as conn:
            result = conn.execute(
                user_supplier_credentials_table.select().where(user_supplier_credentials_table.c.id == credential_id)
            ).fetchone()
            return _deserialize(UserSupplierCredential, result.data) if result else None

    def get_user_supplier_credential_by_user_supplier(self, user_id: str, supplier_id: str) -> Optional[UserSupplierCredential]:
        """Get credential for a specific user-supplier pair"""
        if self._mysql_db:
            return self._mysql_db.get_user_supplier_credentials(user_id, supplier_id)
        with engine.connect() as conn:
            result = conn.execute(
                user_supplier_credentials_table.select().where(
                    (user_supplier_credentials_table.c.user_id == user_id) &
                    (user_supplier_credentials_table.c.supplier_id == supplier_id)
                )
            ).fetchone()
            return _deserialize(UserSupplierCredential, result.data) if result else None

    def list_user_supplier_credentials(self, user_id: str) -> list[UserSupplierCredential]:
        """List all supplier credentials for a user"""
        if self._mysql_db:
            with self._mysql_db.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM user_supplier_credentials WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
                credentials = []
                for row in result:
                    credentials.append(UserSupplierCredential(
                        id=row.id,
                        user_id=row.user_id,
                        supplier_id=row.supplier_id,
                        username=row.username,
                        password_hash=row.password_hash,
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        updated_at=row.updated_at.isoformat() if row.updated_at else None
                    ))
                return credentials
        with engine.connect() as conn:
            results = conn.execute(
                user_supplier_credentials_table.select().where(user_supplier_credentials_table.c.user_id == user_id)
            ).fetchall()
            return [_deserialize(UserSupplierCredential, r.data) for r in results]

    def save_user_supplier_credential(self, credential: UserSupplierCredential) -> UserSupplierCredential:
        with engine.connect() as conn:
            existing = conn.execute(
                user_supplier_credentials_table.select().where(user_supplier_credentials_table.c.id == credential.id)
            ).fetchone()
            if existing:
                conn.execute(
                    user_supplier_credentials_table.update().where(user_supplier_credentials_table.c.id == credential.id).values(
                        user_id=credential.user_id,
                        supplier_id=credential.supplier_id,
                        data=_serialize(credential)
                    )
                )
            else:
                conn.execute(
                    user_supplier_credentials_table.insert().values(
                        id=credential.id,
                        user_id=credential.user_id,
                        supplier_id=credential.supplier_id,
                        data=_serialize(credential)
                    )
                )
            conn.commit()
        return credential

    def delete_user_supplier_credential(self, credential_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                user_supplier_credentials_table.delete().where(user_supplier_credentials_table.c.id == credential_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences by user_id"""
        if self._mysql_db:
            return self._mysql_db.get_user_preferences(user_id)
        with engine.connect() as conn:
            result = conn.execute(
                user_preferences_table.select().where(user_preferences_table.c.user_id == user_id)
            ).fetchone()
            return _deserialize(UserPreferences, result.data) if result else None

    def save_user_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """Save or update user preferences"""
        from datetime import datetime
        preferences.updated_at = datetime.utcnow()
        
        if self._mysql_db:
            return self._mysql_db.create_user_preferences(preferences)
        
        with engine.connect() as conn:
            # Check if preferences already exist
            existing = conn.execute(
                user_preferences_table.select().where(user_preferences_table.c.user_id == preferences.user_id)
            ).fetchone()
            
            if existing:
                # Update existing preferences
                conn.execute(
                    user_preferences_table.update()
                    .where(user_preferences_table.c.user_id == preferences.user_id)
                    .values(data=_serialize(preferences))
                )
            else:
                # Insert new preferences
                conn.execute(
                    user_preferences_table.insert().values(
                        id=preferences.id,
                        user_id=preferences.user_id,
                        data=_serialize(preferences)
                    )
                )
            conn.commit()
            return preferences


db = Database()


def has_any_admin() -> bool:
    """Check if any admin user exists in the database."""
    users = db.list_users()
    return any(u.role == UserRole.ADMIN for u in users)
