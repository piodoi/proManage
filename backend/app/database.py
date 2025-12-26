import os
from typing import Optional, TypeVar, Type
from sqlalchemy import create_engine, Column, String, Text, Integer, MetaData, Table, text
from sqlalchemy.pool import QueuePool
from pydantic import BaseModel

from app.models import (
    User, Property, Unit, Renter, Bill, Payment, EmailConfig, EblocConfig,
    AddressMapping, ExtractionPattern, UserRole
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

units_table = Table(
    "units", metadata,
    Column("id", String(36), primary_key=True),
    Column("property_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

renters_table = Table(
    "renters", metadata,
    Column("id", String(36), primary_key=True),
    Column("unit_id", String(36), index=True),
    Column("access_token", String(36), index=True),
    Column("data", Text, nullable=False),
)

bills_table = Table(
    "bills", metadata,
    Column("id", String(36), primary_key=True),
    Column("unit_id", String(36), index=True),
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

ebloc_configs_table = Table(
    "ebloc_configs", metadata,
    Column("id", String(36), primary_key=True),
    Column("landlord_id", String(36), index=True),
    Column("property_id", String(36), index=True),
    Column("data", Text, nullable=False),
)

address_mappings_table = Table(
    "address_mappings", metadata,
    Column("id", String(36), primary_key=True),
    Column("landlord_id", String(36), index=True),
    Column("property_id", String(36), index=True),
    Column("normalized_address", String(500), index=True),
    Column("data", Text, nullable=False),
)

extraction_patterns_table = Table(
    "extraction_patterns", metadata,
    Column("id", String(36), primary_key=True),
    Column("priority", Integer, index=True),
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

    def list_users(self) -> list[User]:
        with engine.connect() as conn:
            results = conn.execute(users_table.select()).fetchall()
            return [_deserialize(User, r.data) for r in results]

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

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        with engine.connect() as conn:
            result = conn.execute(
                units_table.select().where(units_table.c.id == unit_id)
            ).fetchone()
            return _deserialize(Unit, result.data) if result else None

    def list_units(self, property_id: Optional[str] = None) -> list[Unit]:
        with engine.connect() as conn:
            if property_id:
                results = conn.execute(
                    units_table.select().where(units_table.c.property_id == property_id)
                ).fetchall()
            else:
                results = conn.execute(units_table.select()).fetchall()
            return [_deserialize(Unit, r.data) for r in results]

    def save_unit(self, unit: Unit) -> Unit:
        with engine.connect() as conn:
            existing = conn.execute(
                units_table.select().where(units_table.c.id == unit.id)
            ).fetchone()
            if existing:
                conn.execute(
                    units_table.update().where(units_table.c.id == unit.id).values(
                        property_id=unit.property_id, data=_serialize(unit)
                    )
                )
            else:
                conn.execute(
                    units_table.insert().values(
                        id=unit.id, property_id=unit.property_id, data=_serialize(unit)
                    )
                )
            conn.commit()
        return unit

    def delete_unit(self, unit_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                units_table.delete().where(units_table.c.id == unit_id)
            )
            conn.commit()
            return result.rowcount > 0

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

    def list_renters(self, unit_id: Optional[str] = None) -> list[Renter]:
        with engine.connect() as conn:
            if unit_id:
                results = conn.execute(
                    renters_table.select().where(renters_table.c.unit_id == unit_id)
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
                        unit_id=renter.unit_id, access_token=renter.access_token, data=_serialize(renter)
                    )
                )
            else:
                conn.execute(
                    renters_table.insert().values(
                        id=renter.id, unit_id=renter.unit_id,
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

    def list_bills(self, unit_id: Optional[str] = None) -> list[Bill]:
        with engine.connect() as conn:
            if unit_id:
                results = conn.execute(
                    bills_table.select().where(bills_table.c.unit_id == unit_id)
                ).fetchall()
            else:
                results = conn.execute(bills_table.select()).fetchall()
            return [_deserialize(Bill, r.data) for r in results]

    def save_bill(self, bill: Bill) -> Bill:
        with engine.connect() as conn:
            existing = conn.execute(
                bills_table.select().where(bills_table.c.id == bill.id)
            ).fetchone()
            if existing:
                conn.execute(
                    bills_table.update().where(bills_table.c.id == bill.id).values(
                        unit_id=bill.unit_id, data=_serialize(bill)
                    )
                )
            else:
                conn.execute(
                    bills_table.insert().values(
                        id=bill.id, unit_id=bill.unit_id, data=_serialize(bill)
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

    def get_ebloc_config(self, config_id: str) -> Optional[EblocConfig]:
        with engine.connect() as conn:
            result = conn.execute(
                ebloc_configs_table.select().where(ebloc_configs_table.c.id == config_id)
            ).fetchone()
            return _deserialize(EblocConfig, result.data) if result else None

    def get_ebloc_config_by_property(self, landlord_id: str, property_id: str) -> Optional[EblocConfig]:
        with engine.connect() as conn:
            result = conn.execute(
                ebloc_configs_table.select().where(
                    (ebloc_configs_table.c.landlord_id == landlord_id) &
                    (ebloc_configs_table.c.property_id == property_id)
                )
            ).fetchone()
            return _deserialize(EblocConfig, result.data) if result else None

    def list_ebloc_configs(self, landlord_id: Optional[str] = None) -> list[EblocConfig]:
        with engine.connect() as conn:
            if landlord_id:
                results = conn.execute(
                    ebloc_configs_table.select().where(ebloc_configs_table.c.landlord_id == landlord_id)
                ).fetchall()
            else:
                results = conn.execute(ebloc_configs_table.select()).fetchall()
            return [_deserialize(EblocConfig, r.data) for r in results]

    def save_ebloc_config(self, config: EblocConfig) -> EblocConfig:
        with engine.connect() as conn:
            existing = conn.execute(
                ebloc_configs_table.select().where(ebloc_configs_table.c.id == config.id)
            ).fetchone()
            if existing:
                conn.execute(
                    ebloc_configs_table.update().where(ebloc_configs_table.c.id == config.id).values(
                        landlord_id=config.landlord_id, property_id=config.property_id, data=_serialize(config)
                    )
                )
            else:
                conn.execute(
                    ebloc_configs_table.insert().values(
                        id=config.id, landlord_id=config.landlord_id,
                        property_id=config.property_id, data=_serialize(config)
                    )
                )
            conn.commit()
        return config

    def delete_ebloc_config(self, config_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                ebloc_configs_table.delete().where(ebloc_configs_table.c.id == config_id)
            )
            conn.commit()
            return result.rowcount > 0

    def get_address_mapping(self, mapping_id: str) -> Optional[AddressMapping]:
        with engine.connect() as conn:
            result = conn.execute(
                address_mappings_table.select().where(address_mappings_table.c.id == mapping_id)
            ).fetchone()
            return _deserialize(AddressMapping, result.data) if result else None

    def list_address_mappings(self, landlord_id: Optional[str] = None) -> list[AddressMapping]:
        with engine.connect() as conn:
            if landlord_id:
                results = conn.execute(
                    address_mappings_table.select().where(address_mappings_table.c.landlord_id == landlord_id)
                ).fetchall()
            else:
                results = conn.execute(address_mappings_table.select()).fetchall()
            return [_deserialize(AddressMapping, r.data) for r in results]

    def find_address_mapping(self, landlord_id: str, normalized_address: str) -> Optional[AddressMapping]:
        with engine.connect() as conn:
            result = conn.execute(
                address_mappings_table.select().where(
                    (address_mappings_table.c.landlord_id == landlord_id) &
                    (address_mappings_table.c.normalized_address == normalized_address)
                )
            ).fetchone()
            return _deserialize(AddressMapping, result.data) if result else None

    def save_address_mapping(self, mapping: AddressMapping) -> AddressMapping:
        with engine.connect() as conn:
            existing = conn.execute(
                address_mappings_table.select().where(address_mappings_table.c.id == mapping.id)
            ).fetchone()
            if existing:
                conn.execute(
                    address_mappings_table.update().where(address_mappings_table.c.id == mapping.id).values(
                        landlord_id=mapping.landlord_id, property_id=mapping.property_id,
                        normalized_address=mapping.normalized_address, data=_serialize(mapping)
                    )
                )
            else:
                conn.execute(
                    address_mappings_table.insert().values(
                        id=mapping.id, landlord_id=mapping.landlord_id,
                        property_id=mapping.property_id, normalized_address=mapping.normalized_address,
                        data=_serialize(mapping)
                    )
                )
            conn.commit()
        return mapping

    def delete_address_mapping(self, mapping_id: str) -> bool:
        with engine.connect() as conn:
            result = conn.execute(
                address_mappings_table.delete().where(address_mappings_table.c.id == mapping_id)
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


db = Database()


def has_any_admin() -> bool:
    """Check if any admin user exists in the database."""
    users = db.list_users()
    return any(u.role == UserRole.ADMIN for u in users)
