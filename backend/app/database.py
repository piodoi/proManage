from app.models import (
    User, Property, Unit, Renter, Bill, Payment, EmailConfig, EblocConfig, AddressMapping, UserRole
)

users: dict[str, User] = {}
properties: dict[str, Property] = {}
units: dict[str, Unit] = {}
renters: dict[str, Renter] = {}
bills: dict[str, Bill] = {}
payments: dict[str, Payment] = {}
email_configs: dict[str, EmailConfig] = {}
ebloc_configs: dict[str, EblocConfig] = {}
address_mappings: dict[str, AddressMapping] = {}

renter_tokens: dict[str, str] = {}


def init_db():
    admin = User(
        id="admin-1",
        email="admin@promanage.local",
        name="System Admin",
        role=UserRole.ADMIN,
    )
    users[admin.id] = admin


init_db()
