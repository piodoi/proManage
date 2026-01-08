"""
MySQL Database Layer with Typed Columns

This module provides a MySQL-specific database interface that uses typed columns
instead of the document model (JSON data fields) used by SQLite.

Key differences from database.py:
- Uses typed columns (name, address, amount, etc.) instead of JSON 'data' field
- Optimized indexes for relational queries
- Foreign key constraints
- ENUM types for status fields
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from app.models import (
    User, Property, Renter, Bill, Payment,
    Supplier, PropertySupplier,
    UserPreferences
)


class MySQLDatabase:
    """MySQL database operations using typed columns"""
    
    def __init__(self, database_url: str):
        # Ensure pymysql driver is used
        if '+pymysql' not in database_url:
            database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)
        
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL debugging
        )
        print(f"[Database] MySQL engine initialized: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    # ==================== USER OPERATIONS ====================
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email}
            )
            row = result.fetchone()
            if row:
                return User(
                    id=row.id,
                    email=row.email,
                    name=row.name,
                    role=row.role,
                    password_hash=row.password_hash,
                    oauth_provider=row.oauth_provider,
                    oauth_id=row.oauth_id,
                    subscription_tier=row.subscription_tier,
                    subscription_expires=row.subscription_expires.isoformat() if row.subscription_expires else None,
                    created_at=row.created_at.isoformat() if row.created_at else None
                )
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE id = :id"),
                {"id": user_id}
            )
            row = result.fetchone()
            if row:
                return User(
                    id=row.id,
                    email=row.email,
                    name=row.name,
                    role=row.role,
                    password_hash=row.password_hash,
                    oauth_provider=row.oauth_provider,
                    oauth_id=row.oauth_id,
                    subscription_tier=row.subscription_tier,
                    subscription_expires=row.subscription_expires.isoformat() if row.subscription_expires else None,
                    created_at=row.created_at.isoformat() if row.created_at else None
                )
            return None
    
    def create_user(self, user: User) -> User:
        """Create a new user"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (
                        id, email, name, role, password_hash, oauth_provider, oauth_id,
                        subscription_tier, subscription_expires, created_at
                    ) VALUES (
                        :id, :email, :name, :role, :password_hash, :oauth_provider, :oauth_id,
                        :subscription_tier, :subscription_expires, :created_at
                    )
                """),
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "password_hash": user.password_hash,
                    "oauth_provider": user.oauth_provider,
                    "oauth_id": user.oauth_id,
                    "subscription_tier": user.subscription_tier or 0,
                    "subscription_expires": user.subscription_expires,
                    "created_at": user.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return user
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user fields"""
        if not updates:
            return self.get_user_by_id(user_id)
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE users SET {set_clause} WHERE id = :user_id"),
                {"user_id": user_id, **updates}
            )
            conn.commit()
        return self.get_user_by_id(user_id)
    
    # ==================== PROPERTY OPERATIONS ====================
    
    def get_properties_by_landlord(self, landlord_id: str) -> List[Property]:
        """Get all properties for a landlord"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM properties WHERE landlord_id = :landlord_id ORDER BY created_at DESC"),
                {"landlord_id": landlord_id}
            )
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
    
    def get_property_by_id(self, property_id: str) -> Optional[Property]:
        """Get property by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM properties WHERE id = :id"),
                {"id": property_id}
            )
            row = result.fetchone()
            if row:
                return Property(
                    id=row.id,
                    landlord_id=row.landlord_id,
                    address=row.address,
                    name=row.name,
                    created_at=row.created_at.isoformat() if row.created_at else None
                )
            return None
    
    def create_property(self, prop: Property) -> Property:
        """Create a new property"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO properties (id, landlord_id, address, name, created_at)
                    VALUES (:id, :landlord_id, :address, :name, :created_at)
                """),
                {
                    "id": prop.id,
                    "landlord_id": prop.landlord_id,
                    "address": prop.address,
                    "name": prop.name or "",
                    "created_at": prop.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return prop
    
    def update_property(self, property_id: str, updates: Dict[str, Any]) -> Optional[Property]:
        """Update property fields"""
        if not updates:
            return self.get_property_by_id(property_id)
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE properties SET {set_clause} WHERE id = :property_id"),
                {"property_id": property_id, **updates}
            )
            conn.commit()
        return self.get_property_by_id(property_id)
    
    def delete_property(self, property_id: str) -> bool:
        """Delete property and all related data"""
        with self.engine.connect() as conn:
            # Foreign keys will cascade delete renters, bills, etc.
            conn.execute(
                text("DELETE FROM properties WHERE id = :id"),
                {"id": property_id}
            )
            conn.commit()
        return True
    
    # ==================== RENTER OPERATIONS ====================
    
    def get_renters_by_property(self, property_id: str) -> List[Renter]:
        """Get all renters for a property"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM renters WHERE property_id = :property_id ORDER BY name"),
                {"property_id": property_id}
            )
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
    
    def get_renter_by_id(self, renter_id: str) -> Optional[Renter]:
        """Get renter by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM renters WHERE id = :id"),
                {"id": renter_id}
            )
            row = result.fetchone()
            if row:
                return Renter(
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
                )
            return None
    
    def get_renter_by_token(self, access_token: str) -> Optional[Renter]:
        """Get renter by access token"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM renters WHERE access_token = :token"),
                {"token": access_token}
            )
            row = result.fetchone()
            if row:
                return Renter(
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
                )
            return None
    
    def create_renter(self, renter: Renter) -> Renter:
        """Create a new renter"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO renters (
                        id, property_id, name, email, phone, rent_day,
                        start_contract_date, rent_amount_eur, access_token, created_at
                    ) VALUES (
                        :id, :property_id, :name, :email, :phone, :rent_day,
                        :start_contract_date, :rent_amount_eur, :access_token, :created_at
                    )
                """),
                {
                    "id": renter.id,
                    "property_id": renter.property_id,
                    "name": renter.name,
                    "email": renter.email,
                    "phone": renter.phone,
                    "rent_day": renter.rent_day,
                    "start_contract_date": renter.start_contract_date,
                    "rent_amount_eur": renter.rent_amount_eur,
                    "access_token": renter.access_token,
                    "created_at": renter.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return renter
    
    def update_renter(self, renter_id: str, updates: Dict[str, Any]) -> Optional[Renter]:
        """Update renter fields"""
        if not updates:
            return self.get_renter_by_id(renter_id)
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE renters SET {set_clause} WHERE id = :renter_id"),
                {"renter_id": renter_id, **updates}
            )
            conn.commit()
        return self.get_renter_by_id(renter_id)
    
    def delete_renter(self, renter_id: str) -> bool:
        """Delete renter"""
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM renters WHERE id = :id"),
                {"id": renter_id}
            )
            conn.commit()
        return True
    
    # ==================== BILL OPERATIONS ====================
    
    def get_bills_by_property(self, property_id: str, renter_id: Optional[str] = None) -> List[Bill]:
        """Get bills for a property, optionally filtered by renter"""
        with self.engine.connect() as conn:
            if renter_id:
                # Get bills for specific renter or bills assigned to all renters
                result = conn.execute(
                    text("""
                        SELECT * FROM bills 
                        WHERE property_id = :property_id 
                        AND (renter_id = :renter_id OR renter_id IS NULL OR renter_id = 'all')
                        ORDER BY due_date DESC
                    """),
                    {"property_id": property_id, "renter_id": renter_id}
                )
            else:
                result = conn.execute(
                    text("SELECT * FROM bills WHERE property_id = :property_id ORDER BY due_date DESC"),
                    {"property_id": property_id}
                )
            
            bills = []
            for row in result:
                bills.append(self._row_to_bill(row))
            return bills
    
    def get_bill_by_id(self, bill_id: str) -> Optional[Bill]:
        """Get bill by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM bills WHERE id = :id"),
                {"id": bill_id}
            )
            row = result.fetchone()
            if row:
                return self._row_to_bill(row)
            return None
    
    def create_bill(self, bill: Bill) -> Bill:
        """Create a new bill"""
        with self.engine.connect() as conn:
            # Convert renter_id='all' to None
            renter_id = bill.renter_id if bill.renter_id and bill.renter_id != 'all' else None
            
            conn.execute(
                text("""
                    INSERT INTO bills (
                        id, property_id, renter_id, supplier_id, bill_type, description,
                        amount, currency, due_date, bill_date, legal_name, iban, bill_number,
                        extraction_pattern_id, contract_id, payment_details, status, source_email_id, created_at
                    ) VALUES (
                        :id, :property_id, :renter_id, :supplier_id, :bill_type, :description,
                        :amount, :currency, :due_date, :bill_date, :legal_name, :iban, :bill_number,
                        :extraction_pattern_id, :contract_id, :payment_details, :status, :source_email_id, :created_at
                    )
                """),
                {
                    "id": bill.id,
                    "property_id": bill.property_id,
                    "renter_id": renter_id,
                    "supplier_id": bill.supplier_id,
                    "bill_type": bill.bill_type or "utilities",
                    "description": bill.description,
                    "amount": bill.amount,
                    "currency": bill.currency or "RON",
                    "due_date": bill.due_date,
                    "bill_date": bill.bill_date,
                    "legal_name": bill.legal_name,
                    "iban": bill.iban,
                    "bill_number": bill.bill_number,
                    "extraction_pattern_id": bill.extraction_pattern_id,
                    "contract_id": bill.contract_id,
                    "payment_details": json.dumps(bill.payment_details) if bill.payment_details else None,
                    "status": bill.status or "pending",
                    "source_email_id": bill.source_email_id,
                    "created_at": bill.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return bill
    
    def update_bill(self, bill_id: str, updates: Dict[str, Any]) -> Optional[Bill]:
        """Update bill fields"""
        if not updates:
            return self.get_bill_by_id(bill_id)
        
        # Handle renter_id='all' -> None conversion
        if 'renter_id' in updates and updates['renter_id'] == 'all':
            updates['renter_id'] = None
        
        # Handle payment_details JSON serialization
        if 'payment_details' in updates and updates['payment_details']:
            updates['payment_details'] = json.dumps(updates['payment_details'])
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE bills SET {set_clause} WHERE id = :bill_id"),
                {"bill_id": bill_id, **updates}
            )
            conn.commit()
        return self.get_bill_by_id(bill_id)
    
    def delete_bill(self, bill_id: str) -> bool:
        """Delete bill"""
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM bills WHERE id = :id"),
                {"id": bill_id}
            )
            conn.commit()
        return True
    
    def _row_to_bill(self, row) -> Bill:
        """Convert database row to Bill model"""
        payment_details = None
        if row.payment_details:
            try:
                payment_details = json.loads(row.payment_details) if isinstance(row.payment_details, str) else row.payment_details
            except:
                payment_details = None
        
        return Bill(
            id=row.id,
            property_id=row.property_id,
            renter_id=row.renter_id,
            supplier_id=row.supplier_id,
            bill_type=row.bill_type,
            description=row.description,
            amount=float(row.amount) if row.amount else 0,
            currency=row.currency,
            due_date=row.due_date.isoformat() if row.due_date else None,
            bill_date=row.bill_date.isoformat() if row.bill_date else None,
            legal_name=row.legal_name,
            iban=row.iban,
            bill_number=row.bill_number,
            extraction_pattern_id=row.extraction_pattern_id,
            contract_id=row.contract_id,
            payment_details=payment_details,
            status=row.status,
            source_email_id=row.source_email_id,
            created_at=row.created_at.isoformat() if row.created_at else None
        )
    
    # ==================== PAYMENT OPERATIONS ====================
    
    def get_payments_by_bill(self, bill_id: str) -> List[Payment]:
        """Get all payments for a bill"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM payments WHERE bill_id = :bill_id ORDER BY created_at DESC"),
                {"bill_id": bill_id}
            )
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
    
    def create_payment(self, payment: Payment) -> Payment:
        """Create a new payment"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO payments (id, bill_id, amount, method, status, commission, created_at)
                    VALUES (:id, :bill_id, :amount, :method, :status, :commission, :created_at)
                """),
                {
                    "id": payment.id,
                    "bill_id": payment.bill_id,
                    "amount": payment.amount,
                    "method": payment.method or "bank_transfer",
                    "status": payment.status or "pending",
                    "commission": payment.commission or 0,
                    "created_at": payment.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return payment
    
    # ==================== SUPPLIER OPERATIONS ====================
    
    def get_all_suppliers(self) -> List[Supplier]:
        """Get all suppliers"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM suppliers ORDER BY name"))
            suppliers = []
            for row in result:
                suppliers.append(Supplier(
                    id=row.id,
                    name=row.name,
                    has_api=bool(row.has_api),
                    bill_type=row.bill_type,
                    extraction_pattern_supplier=row.extraction_pattern_supplier,
                    created_at=row.created_at.isoformat() if row.created_at else None
                ))
            return suppliers
    
    def get_supplier_by_id(self, supplier_id: str) -> Optional[Supplier]:
        """Get supplier by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM suppliers WHERE id = :id"),
                {"id": supplier_id}
            )
            row = result.fetchone()
            if row:
                return Supplier(
                    id=row.id,
                    name=row.name,
                    has_api=bool(row.has_api),
                    bill_type=row.bill_type,
                    extraction_pattern_supplier=row.extraction_pattern_supplier,
                    created_at=row.created_at.isoformat() if row.created_at else None
                )
            return None
    
    def create_supplier(self, supplier: Supplier) -> Supplier:
        """Create a new supplier"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO suppliers (id, name, has_api, bill_type, extraction_pattern_supplier, created_at)
                    VALUES (:id, :name, :has_api, :bill_type, :extraction_pattern_supplier, :created_at)
                """),
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "has_api": 1 if supplier.has_api else 0,
                    "bill_type": supplier.bill_type or "utilities",
                    "extraction_pattern_supplier": supplier.extraction_pattern_supplier,
                    "created_at": supplier.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return supplier
    
    def update_supplier(self, supplier: Supplier) -> Supplier:
        """Update existing supplier"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE suppliers 
                    SET name = :name, 
                        has_api = :has_api, 
                        bill_type = :bill_type, 
                        extraction_pattern_supplier = :extraction_pattern_supplier
                    WHERE id = :id
                """),
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "has_api": 1 if supplier.has_api else 0,
                    "bill_type": supplier.bill_type or "utilities",
                    "extraction_pattern_supplier": supplier.extraction_pattern_supplier
                }
            )
            conn.commit()
        return supplier
    
    def delete_supplier(self, supplier_id: str) -> bool:
        """Delete supplier - foreign keys will handle cascading or set null"""
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM suppliers WHERE id = :id"),
                {"id": supplier_id}
            )
            conn.commit()
        return True
    
    # ==================== PROPERTY SUPPLIERS ====================
    
    def get_property_suppliers(self, property_id: str) -> List[PropertySupplier]:
        """Get all suppliers for a property"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM property_suppliers WHERE property_id = :property_id"),
                {"property_id": property_id}
            )
            suppliers = []
            for row in result:
                suppliers.append(PropertySupplier(
                    id=row.id,
                    property_id=row.property_id,
                    supplier_id=row.supplier_id,
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                ))
            return suppliers
    
    def get_property_supplier(self, property_id: str, supplier_id: str) -> Optional[PropertySupplier]:
        """Get specific property-supplier relationship"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT * FROM property_suppliers 
                    WHERE property_id = :property_id AND supplier_id = :supplier_id
                """),
                {"property_id": property_id, "supplier_id": supplier_id}
            )
            row = result.fetchone()
            if row:
                return PropertySupplier(
                    id=row.id,
                    property_id=row.property_id,
                    supplier_id=row.supplier_id,
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    def create_property_supplier(self, ps: PropertySupplier) -> PropertySupplier:
        """Create property-supplier relationship"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO property_suppliers (
                        id, property_id, supplier_id, contract_id, direct_debit, created_at, updated_at
                    ) VALUES (
                        :id, :property_id, :supplier_id, :contract_id, :direct_debit, :created_at, :updated_at
                    )
                    ON DUPLICATE KEY UPDATE
                        contract_id = VALUES(contract_id),
                        direct_debit = VALUES(direct_debit),
                        updated_at = VALUES(updated_at)
                """),
                {
                    "id": ps.id,
                    "property_id": ps.property_id,
                    "supplier_id": ps.supplier_id,
                    "contract_id": ps.contract_id,
                    "direct_debit": 1 if ps.direct_debit else 0,
                    "created_at": ps.created_at or datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            )
            conn.commit()
        return ps
    
    def update_property_supplier(self, ps_id: str, updates: Dict[str, Any]) -> Optional[PropertySupplier]:
        """Update property supplier relationship"""
        if not updates:
            return None
        
        # Add updated_at
        updates['updated_at'] = datetime.now().isoformat()
        
        # Handle boolean conversion
        if 'direct_debit' in updates:
            updates['direct_debit'] = 1 if updates['direct_debit'] else 0
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE property_suppliers SET {set_clause} WHERE id = :ps_id"),
                {"ps_id": ps_id, **updates}
            )
            conn.commit()
            
            # Fetch and return updated record
            result = conn.execute(
                text("SELECT * FROM property_suppliers WHERE id = :id"),
                {"id": ps_id}
            )
            row = result.fetchone()
            if row:
                return PropertySupplier(
                    id=row.id,
                    property_id=row.property_id,
                    supplier_id=row.supplier_id,
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    # ==================== USER PREFERENCES ====================
    
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM user_preferences WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row:
                return UserPreferences(
                    id=row.id,
                    user_id=row.user_id,
                    language=row.language,
                    view_mode=row.view_mode,
                    rent_warning_days=row.rent_warning_days,
                    rent_currency=row.rent_currency,
                    bill_currency=row.bill_currency,
                    date_format=row.date_format,
                    phone_number=row.phone_number,
                    landlord_name=row.landlord_name,
                    personal_email=row.personal_email,
                    iban=row.iban,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    def create_user_preferences(self, prefs: UserPreferences) -> UserPreferences:
        """Create or update user preferences"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO user_preferences (
                        id, user_id, language, view_mode, rent_warning_days, rent_currency, bill_currency,
                        date_format, phone_number, landlord_name, personal_email, iban, updated_at
                    ) VALUES (
                        :id, :user_id, :language, :view_mode, :rent_warning_days, :rent_currency, :bill_currency,
                        :date_format, :phone_number, :landlord_name, :personal_email, :iban, :updated_at
                    )
                    ON DUPLICATE KEY UPDATE
                        language = VALUES(language),
                        view_mode = VALUES(view_mode),
                        rent_warning_days = VALUES(rent_warning_days),
                        rent_currency = VALUES(rent_currency),
                        bill_currency = VALUES(bill_currency),
                        date_format = VALUES(date_format),
                        phone_number = VALUES(phone_number),
                        landlord_name = VALUES(landlord_name),
                        personal_email = VALUES(personal_email),
                        iban = VALUES(iban),
                        updated_at = VALUES(updated_at)
                """),
                {
                    "id": prefs.id,
                    "user_id": prefs.user_id,
                    "language": prefs.language or "en",
                    "view_mode": prefs.view_mode or "list",
                    "rent_warning_days": prefs.rent_warning_days or 5,
                    "rent_currency": prefs.rent_currency or "EUR",
                    "bill_currency": prefs.bill_currency or "RON",
                    "date_format": prefs.date_format or "DD/MM/YYYY",
                    "phone_number": prefs.phone_number,
                    "landlord_name": prefs.landlord_name,
                    "personal_email": prefs.personal_email,
                    "iban": prefs.iban,
                    "updated_at": datetime.now().isoformat()
                }
            )
            conn.commit()
        return prefs
