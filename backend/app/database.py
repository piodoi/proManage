import os
from typing import Optional, TypeVar, Type
from sqlalchemy import create_engine, Column, String, Text, Integer, MetaData, Table, text, func
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel

from app.models import (
    User, Property, Renter, Bill, Payment, EmailConfig,
    ExtractionPattern, UserRole, Supplier, PropertySupplier, UserSupplierCredential,
    UserPreferences
)

T = TypeVar("T", bound=BaseModel)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./promanage.db"
)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
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

email_configs_table = Table(
    "email_configs", metadata,
    Column("id", String(36), primary_key=True),
    Column("landlord_id", String(36), index=True),
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
        metadata.create_all(engine)

    def get_user(self, user_id: str) -> Optional[User]:
        with engine.connect() as conn:
            result = conn.execute(
                users_table.select().where(users_table.c.id == user_id)
            ).fetchone()
            return _deserialize(User, result.data) if result else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with engine.connect() as conn:
            result = conn.execute(
                users_table.select().where(users_table.c.email == email)
            ).fetchone()
            return _deserialize(User, result.data) if result else None

    def list_users(self, limit: Optional[int] = None, offset: Optional[int] = None) -> list[User]:
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
        with engine.connect() as conn:
            result = conn.execute(
                properties_table.select().where(properties_table.c.id == property_id)
            ).fetchone()
            return _deserialize(Property, result.data) if result else None

    def list_properties(self, landlord_id: Optional[str] = None) -> list[Property]:
        with engine.connect() as conn:
            if landlord_id:
                results = conn.execute(
                    properties_table.select().where(properties_table.c.landlord_id == landlord_id)
                ).fetchall()
            else:
                results = conn.execute(properties_table.select()).fetchall()
            return [_deserialize(Property, r.data) for r in results]

    def save_property(self, prop: Property) -> Property:
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
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.select().where(renters_table.c.id == renter_id)
            ).fetchone()
            return _deserialize(Renter, result.data) if result else None

    def get_renter_by_token(self, token: str) -> Optional[Renter]:
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.select().where(renters_table.c.access_token == token)
            ).fetchone()
            return _deserialize(Renter, result.data) if result else None

    def list_renters(self, property_id: Optional[str] = None) -> list[Renter]:
        with engine.connect() as conn:
            if property_id:
                results = conn.execute(
                    renters_table.select().where(renters_table.c.property_id == property_id)
                ).fetchall()
            else:
                results = conn.execute(renters_table.select()).fetchall()
            return [_deserialize(Renter, r.data) for r in results]

    def save_renter(self, renter: Renter) -> Renter:
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
        with engine.connect() as conn:
            result = conn.execute(
                renters_table.delete().where(renters_table.c.id == renter_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_bill(self, bill_id: str) -> Optional[Bill]:
        with engine.connect() as conn:
            result = conn.execute(
                bills_table.select().where(bills_table.c.id == bill_id)
            ).fetchone()
            return _deserialize(Bill, result.data) if result else None

    def list_bills(self, property_id: Optional[str] = None, renter_id: Optional[str] = None) -> list[Bill]:
        with engine.connect() as conn:
            query = bills_table.select()
            if property_id:
                query = query.where(bills_table.c.property_id == property_id)
            if renter_id:
                query = query.where(bills_table.c.renter_id == renter_id)
            results = conn.execute(query).fetchall()
            return [_deserialize(Bill, r.data) for r in results]

    def save_bill(self, bill: Bill) -> Bill:
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
        with engine.connect() as conn:
            if bill_id:
                results = conn.execute(
                    payments_table.select().where(payments_table.c.bill_id == bill_id)
                ).fetchall()
            else:
                results = conn.execute(payments_table.select()).fetchall()
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

    def get_email_config(self, config_id: str) -> Optional[EmailConfig]:
        with engine.connect() as conn:
            result = conn.execute(
                email_configs_table.select().where(email_configs_table.c.id == config_id)
            ).fetchone()
            return _deserialize(EmailConfig, result.data) if result else None

    def get_email_config_by_landlord(self, landlord_id: str) -> Optional[EmailConfig]:
        with engine.connect() as conn:
            result = conn.execute(
                email_configs_table.select().where(email_configs_table.c.landlord_id == landlord_id)
            ).fetchone()
            return _deserialize(EmailConfig, result.data) if result else None

    def list_email_configs(self) -> list[EmailConfig]:
        with engine.connect() as conn:
            results = conn.execute(email_configs_table.select()).fetchall()
            return [_deserialize(EmailConfig, r.data) for r in results]

    def save_email_config(self, config: EmailConfig) -> EmailConfig:
        with engine.connect() as conn:
            existing = conn.execute(
                email_configs_table.select().where(email_configs_table.c.id == config.id)
            ).fetchone()
            if existing:
                conn.execute(
                    email_configs_table.update().where(email_configs_table.c.id == config.id).values(
                        landlord_id=config.landlord_id, data=_serialize(config)
                    )
                )
            else:
                conn.execute(
                    email_configs_table.insert().values(
                        id=config.id, landlord_id=config.landlord_id, data=_serialize(config)
                    )
                )
            conn.commit()
        return config

    def delete_email_config(self, config_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                email_configs_table.delete().where(email_configs_table.c.id == config_id)
            )
            conn.commit()
            return result.rowcount > 0

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
        with engine.connect() as conn:
            result = conn.execute(
                suppliers_table.select().where(suppliers_table.c.id == supplier_id)
            ).fetchone()
            return _deserialize(Supplier, result.data) if result else None

    def get_supplier_by_name(self, name: str) -> Optional[Supplier]:
        with engine.connect() as conn:
            result = conn.execute(
                suppliers_table.select().where(suppliers_table.c.name == name)
            ).fetchone()
            return _deserialize(Supplier, result.data) if result else None

    def list_suppliers(self) -> list[Supplier]:
        with engine.connect() as conn:
            results = conn.execute(suppliers_table.select()).fetchall()
            return [_deserialize(Supplier, r.data) for r in results]

    def save_supplier(self, supplier: Supplier) -> Supplier:
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
        with engine.connect() as conn:
            result = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.id == property_supplier_id)
            ).fetchone()
            return _deserialize(PropertySupplier, result.data) if result else None

    def list_property_suppliers(self, property_id: str) -> list[PropertySupplier]:
        with engine.connect() as conn:
            results = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.property_id == property_id)
            ).fetchall()
            return [_deserialize(PropertySupplier, r.data) for r in results]

    def get_property_supplier_by_supplier(self, property_id: str, supplier_id: str) -> Optional[PropertySupplier]:
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
        with engine.connect() as conn:
            results = conn.execute(
                property_suppliers_table.select().where(property_suppliers_table.c.supplier_id == supplier_id)
            ).fetchall()
            return [_deserialize(PropertySupplier, r.data) for r in results]

    # UserSupplierCredential methods
    def get_user_supplier_credential(self, credential_id: str) -> Optional[UserSupplierCredential]:
        with engine.connect() as conn:
            result = conn.execute(
                user_supplier_credentials_table.select().where(user_supplier_credentials_table.c.id == credential_id)
            ).fetchone()
            return _deserialize(UserSupplierCredential, result.data) if result else None

    def get_user_supplier_credential_by_user_supplier(self, user_id: str, supplier_id: str) -> Optional[UserSupplierCredential]:
        """Get credential for a specific user-supplier pair"""
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
        with engine.connect() as conn:
            result = conn.execute(
                user_preferences_table.select().where(user_preferences_table.c.user_id == user_id)
            ).fetchone()
            return _deserialize(UserPreferences, result.data) if result else None

    def save_user_preferences(self, preferences: UserPreferences) -> UserPreferences:
        """Save or update user preferences"""
        from datetime import datetime
        preferences.updated_at = datetime.utcnow()
        
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
