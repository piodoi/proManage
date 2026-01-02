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


# Subscription is now an int: 0 = off, 1 = on (reserved for future tiers)
# Keeping enum for backward compatibility but will be converted to int
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
    subscription_status: SubscriptionStatus = SubscriptionStatus.NONE  # Deprecated, use subscription_tier
    subscription_tier: int = 0  # 0 = off, 1 = on (reserved for future tiers)
    subscription_expires: Optional[datetime] = None
    ebloc_username: Optional[str] = None  # E-bloc login credentials (one per user)
    ebloc_password_hash: Optional[str] = None  # Encrypted password for E-bloc
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
    rent_day: Optional[int] = Field(None, ge=1, le=28)  # Day of month (1-28) for recurring rent
    start_contract_date: Optional[date] = None  # Optional start date of contract
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
    currency: Optional[str] = "RON"  # Currency for the bill: "EUR", "RON", or "USD"
    due_date: datetime
    bill_date: Optional[datetime] = None  # Date of the bill (when it was issued)
    legal_name: Optional[str] = None  # Legal name of the supplier/company
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    extraction_pattern_id: Optional[str] = None  # ID of the extraction pattern used to parse this bill
    contract_id: Optional[str] = None  # Contract/client ID extracted from PDF for payment
    payment_details: Optional[dict] = None  # Additional payment details (e.g., client_code) stored as JSON
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






class ExtractionPattern(BaseModel):
    id: str = Field(default_factory=gen_id)
    name: str
    bill_type: BillType
    supplier: Optional[str] = None  # Supplier name (e.g., "Vodafone", "Hidroelectrica")
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    contract_id_pattern: Optional[str] = None  # Pattern to extract contract/client ID
    client_code_pattern: Optional[str] = None  # Pattern to extract client code (for payment details)
    due_date_pattern: Optional[str] = None  # Pattern to extract due date
    business_name_pattern: Optional[str] = None  # Pattern for business name for bank transfer
    bank_accounts: Optional[list[dict[str, str]]] = None  # List of {bank: name, iban: number} for validation
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None  # Timestamp when pattern was last updated from JSON file


class ExtractionPatternCreate(BaseModel):
    name: str
    bill_type: BillType
    supplier: Optional[str] = None
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    contract_id_pattern: Optional[str] = None
    client_code_pattern: Optional[str] = None
    due_date_pattern: Optional[str] = None
    business_name_pattern: Optional[str] = None
    bank_accounts: Optional[list[dict[str, str]]] = None
    priority: int = 0


class ExtractionPatternUpdate(BaseModel):
    name: Optional[str] = None
    bill_type: Optional[BillType] = None
    supplier: Optional[str] = None
    vendor_hint: Optional[str] = None
    iban_pattern: Optional[str] = None
    amount_pattern: Optional[str] = None
    address_pattern: Optional[str] = None
    bill_number_pattern: Optional[str] = None
    contract_id_pattern: Optional[str] = None
    client_code_pattern: Optional[str] = None
    due_date_pattern: Optional[str] = None
    business_name_pattern: Optional[str] = None
    bank_accounts: Optional[list[dict[str, str]]] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class ExtractionResult(BaseModel):
    iban: Optional[str] = None
    contract_id: Optional[str] = None  # Contract/client ID for bank transfer
    client_code: Optional[str] = None  # Client code (for payment details)
    bill_number: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None  # Due date in ISO format or original format
    address: Optional[str] = None
    consumption_location: Optional[str] = None
    business_name: Optional[str] = None  # Business name for bank transfer
    all_addresses: list[str] = Field(default_factory=list)
    bank_accounts: list[dict[str, str]] = Field(default_factory=list)  # List of {bank: name, iban: number}
    matched_pattern_id: Optional[str] = None
    matched_pattern_name: Optional[str] = None
    matched_pattern_supplier: Optional[str] = None  # Supplier name from matched pattern
    raw_text: Optional[str] = None


class UserCreate(BaseModel):
    email: str
    name: str
    role: UserRole
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None


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
    rent_day: Optional[int] = Field(None, ge=1, le=28)  # Day of month (1-28) for recurring rent
    start_contract_date: Optional[date] = None  # Optional start date of contract
    rent_amount_eur: Optional[float] = None


class RenterUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    rent_day: Optional[int] = Field(None, ge=1, le=28)  # Day of month (1-28) for recurring rent
    start_contract_date: Optional[date] = None  # Optional start date of contract
    rent_amount_eur: Optional[float] = None


class BillCreate(BaseModel):
    property_id: str
    renter_id: Optional[str] = None  # None means bill applies to all renters in the property
    bill_type: BillType
    description: str
    amount: float
    currency: Optional[str] = "RON"  # Currency for the bill: "EUR", "RON", or "USD"
    due_date: datetime
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    extraction_pattern_id: Optional[str] = None
    contract_id: Optional[str] = None


class BillUpdate(BaseModel):
    renter_id: Optional[str] = None  # None means bill applies to all renters in the property
    bill_type: Optional[BillType] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: Optional[datetime] = None
    iban: Optional[str] = None
    bill_number: Optional[str] = None
    extraction_pattern_id: Optional[str] = None
    contract_id: Optional[str] = None
    payment_details: Optional[dict] = None
    status: Optional[BillStatus] = None


class PaymentCreate(BaseModel):
    bill_id: str
    amount: float
    method: PaymentMethod


class EmailConfigCreate(BaseModel):
    config_type: EmailConfigType
    forwarding_email: Optional[str] = None


class EblocConfigCreate(BaseModel):
    username: str
    password: str


class Supplier(BaseModel):
    """Represents a supported supplier (from extraction patterns or hardcoded list)"""
    id: str = Field(default_factory=gen_id)
    name: str  # Supplier name (e.g., "Vodafone", "Digi", "Panova")
    has_api: bool = False  # Whether API integration is available for automatic bill fetching
    bill_type: BillType = BillType.UTILITIES  # Type of bills this supplier provides
    extraction_pattern_supplier: Optional[str] = None  # Supplier name from extraction pattern (for matching)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserSupplierCredential(BaseModel):
    """Represents user credentials for a supplier (shared across all user's properties)"""
    id: str = Field(default_factory=gen_id)
    user_id: str  # Reference to User.id
    supplier_id: str  # Reference to Supplier.id
    username: Optional[str] = None  # Encrypted username for API access
    password_hash: Optional[str] = None  # Encrypted password for API access
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PropertySupplier(BaseModel):
    """Represents a supplier configured for a specific property"""
    id: str = Field(default_factory=gen_id)
    property_id: str
    supplier_id: str  # Reference to Supplier.id
    credential_id: Optional[str] = None  # Reference to UserSupplierCredential.id (shared credentials)
    contract_id: Optional[str] = None  # Contract ID to differentiate what to scrape for this property (filled on first scrape)
    direct_debit: bool = False  # Whether bills will be paid automatically on due date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SupplierCreate(BaseModel):
    name: str
    has_api: bool = False
    bill_type: BillType = BillType.UTILITIES
    extraction_pattern_supplier: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    has_api: Optional[bool] = None
    bill_type: Optional[BillType] = None
    extraction_pattern_supplier: Optional[str] = None


class PropertySupplierCreate(BaseModel):
    supplier_id: str
    credential_id: Optional[str] = None  # Link to existing user-supplier credential
    contract_id: Optional[str] = None  # Contract ID to differentiate what to scrape for this property
    direct_debit: bool = False  # Whether bills will be paid automatically on due date


class PropertySupplierUpdate(BaseModel):
    credential_id: Optional[str] = None  # Link to existing user-supplier credential
    contract_id: Optional[str] = None  # Contract ID to differentiate what to scrape for this property
    direct_debit: Optional[bool] = None  # Whether bills will be paid automatically on due date


class UserSupplierCredentialCreate(BaseModel):
    supplier_id: str
    username: Optional[str] = None
    password: Optional[str] = None


class UserSupplierCredentialUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None




class TokenData(BaseModel):
    user_id: str
    email: str
    role: UserRole


class UserPreferences(BaseModel):
    id: str = Field(default_factory=gen_id)
    user_id: str  # Reference to User.id
    language: Optional[str] = "en"  # Language code: "en" or "ro"
    view_mode: Optional[str] = "list"  # View mode: "list" or "grid"
    rent_warning_days: Optional[int] = 5  # Number of days before rent due date to show warning
    rent_currency: Optional[str] = "EUR"  # Preferred currency for rent: "EUR", "RON", or "USD"
    bill_currency: Optional[str] = "RON"  # Preferred currency for bills: "EUR", "RON", or "USD"
    phone_number: Optional[str] = None  # User's phone number with country code for WhatsApp
    updated_at: datetime = Field(default_factory=datetime.utcnow)