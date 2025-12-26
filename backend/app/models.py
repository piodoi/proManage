from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum
import uuid


class UserRole(str, Enum):
    ADMIN = "admin"
    LANDLORD = "landlord"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"


class BillStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class BillType(str, Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    EBLOC = "ebloc"
    OTHER = "other"


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    PAYMENT_SERVICE = "payment_service"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class EmailConfigType(str, Enum):
    DIRECT = "direct"
    FORWARDING = "forwarding"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    NONE = "none"


def gen_id() -> str:
    return str(uuid.uuid4())


def gen_token() -> str:
    return str(uuid.uuid4())


class User(BaseModel):
    id: str = Field(default_factory=gen_id)
    email: str
    name: str
    role: UserRole
    password_hash: Optional[str] = None
    oauth_provider: Optional[OAuthProvider] = None
    oauth_id: Optional[str] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.NONE
    subscription_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Property(BaseModel):
    id: str = Field(default_factory=gen_id)
    landlord_id: str
    address: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Unit(BaseModel):
    id: str = Field(default_factory=gen_id)
    property_id: str
    unit_number: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Renter(BaseModel):
    id: str = Field(default_factory=gen_id)
    property_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    rent_date: Optional[date] = None
    rent_amount_eur: Optional[float] = None
    access_token: str = Field(default_factory=gen_token)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Bill(BaseModel):
    id: str = Field(default_factory=gen_id)
    property_id: str
    renter_id: Optional[str] = None  # None means bill applies to all renters in the property
    bill_type: BillType
    description: str
    amount: float
    due_date: datetime
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    status: BillStatus = BillStatus.PENDING
    source_email_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Payment(BaseModel):
    id: str = Field(default_factory=gen_id)
    bill_id: str
    amount: float
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    commission: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmailConfig(BaseModel):
    id: str = Field(default_factory=gen_id)
    landlord_id: str
    config_type: EmailConfigType
    forwarding_email: Optional[str] = None
    gmail_credentials: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EblocConfig(BaseModel):
    id: str = Field(default_factory=gen_id)
    landlord_id: str
    property_id: str
    username: str
    password_hash: str
    ebloc_page_id: Optional[str] = None
    ebloc_url: Optional[str] = None  # URL to the e-bloc property page
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AddressMapping(BaseModel):
    id: str = Field(default_factory=gen_id)
    landlord_id: str
    property_id: str
    extracted_address: str
    normalized_address: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionPattern(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    bill_type: BillType
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionPatternCreate(BaseModel):
    name: str
    bill_type: BillType
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    priority: int = 0


class ExtractionPatternUpdate(BaseModel):
    name: Optional[str] = None
    bill_type: Optional[BillType] = None
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class ExtractionResult(BaseModel):
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    amount: Optional[float] = None
    address: Optional[str] = None
    consumption_location: Optional[str] = None
    all_addresses: list[str] = Field(default_factory=list)
    matched_pattern_id: Optional[str] = None
    matched_pattern_name: Optional[str] = None
    raw_text: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    name: str
    role: UserRole


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None


class PropertyCreate(BaseModel):
    address: str
    name: str


class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    name: Optional[str] = None


class UnitCreate(BaseModel):
    unit_number: str


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = None


class RenterCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    rent_date: Optional[date] = None
    rent_amount_eur: Optional[float] = None


class RenterUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rent_date: Optional[date] = None
    rent_amount_eur: Optional[float] = None


class BillCreate(BaseModel):
    property_id: str
    renter_id: Optional[str] = None  # None means bill applies to all renters in the property
    bill_type: BillType
    description: str
    amount: float
    due_date: datetime
    iban: Optional[str] = None
    bill_number: Optional[str] = None


class BillUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    status: Optional[BillStatus] = None


class PaymentCreate(BaseModel):
    bill_id: str
    amount: float
    method: PaymentMethod


class EmailConfigCreate(BaseModel):
    config_type: EmailConfigType
    forwarding_email: Optional[str] = None


class EblocConfigCreate(BaseModel):
    property_id: Optional[str] = None
    username: str
    password: str
    ebloc_page_id: Optional[str] = None
    # For instant import - pass property data directly
    ebloc_property_name: Optional[str] = None
    ebloc_property_address: Optional[str] = None
    ebloc_property_url: Optional[str] = None


class AddressMappingCreate(BaseModel):
    property_id: str
    extracted_address: str


class TokenData(BaseModel):
    user_id: str
    email: str
    role: UserRole
