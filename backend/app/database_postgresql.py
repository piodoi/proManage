"""
PostgreSQL/Neon Database Layer with Typed Columns

This module provides a PostgreSQL-specific database interface that uses typed columns.
Optimized for Neon serverless PostgreSQL with connection pooling.

Key features:
- Uses typed columns (name, address, amount, etc.) instead of JSON 'data' field
- Optimized indexes for relational queries
- Foreign key constraints
- Compatible with Neon's serverless architecture
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from app.models import (
    User, Property, Renter, Bill, PaymentNotification,
    Supplier, PropertySupplier,
    UserPreferences
)


class PostgreSQLDatabase:
    """PostgreSQL database operations using typed columns"""
    
    def __init__(self, database_url: str):
        # Ensure psycopg2 driver is used if not specified
        if database_url.startswith('postgresql://') and '+' not in database_url.split('://')[0]:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
        
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300,  # Recycle connections every 5 minutes (good for serverless)
            echo=False,  # Set to True for SQL debugging
        )
        # Extract host for logging (hide credentials)
        host_part = database_url.split('@')[1].split('/')[0] if '@' in database_url else 'localhost'
        print(f"[Database] PostgreSQL engine initialized: {host_part}")
    
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
                return self._row_to_user(row)
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
                return self._row_to_user(row)
            return None
    
    def _row_to_user(self, row) -> User:
        """Convert database row to User model"""
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
                renters.append(self._row_to_renter(row))
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
                return self._row_to_renter(row)
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
                return self._row_to_renter(row)
            return None
    
    def _row_to_renter(self, row) -> Renter:
        """Convert database row to Renter model"""
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
            renter_id = bill.renter_id if bill.renter_id and bill.renter_id != 'all' else None
            
            conn.execute(
                text("""
                    INSERT INTO bills (
                        id, property_id, renter_id, property_supplier_id, bill_type, description,
                        amount, currency, due_date, bill_date, legal_name, iban, bill_number,
                        extraction_pattern_id, contract_id, payment_details, status, created_at
                    ) VALUES (
                        :id, :property_id, :renter_id, :property_supplier_id, :bill_type, :description,
                        :amount, :currency, :due_date, :bill_date, :legal_name, :iban, :bill_number,
                        :extraction_pattern_id, :contract_id, :payment_details, :status, :created_at
                    )
                """),
                {
                    "id": bill.id,
                    "property_id": bill.property_id,
                    "renter_id": renter_id,
                    "property_supplier_id": bill.property_supplier_id,
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
                    "created_at": bill.created_at or datetime.now().isoformat()
                }
            )
            conn.commit()
        return bill
    
    def update_bill(self, bill_id: str, updates: Dict[str, Any]) -> Optional[Bill]:
        """Update bill fields"""
        if not updates:
            return self.get_bill_by_id(bill_id)
        
        if 'renter_id' in updates and updates['renter_id'] == 'all':
            updates['renter_id'] = None
        
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
            property_supplier_id=getattr(row, 'property_supplier_id', None),
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
            created_at=row.created_at.isoformat() if row.created_at else None
        )
    
    # ==================== PAYMENT NOTIFICATION OPERATIONS ====================
    
    def get_payment_notifications_by_landlord(self, landlord_id: str, status: Optional[str] = None) -> List[PaymentNotification]:
        """Get all payment notifications for a landlord, optionally filtered by status"""
        with self.engine.connect() as conn:
            if status:
                result = conn.execute(
                    text("SELECT * FROM payment_notifications WHERE landlord_id = :landlord_id AND status = :status ORDER BY created_at DESC"),
                    {"landlord_id": landlord_id, "status": status}
                )
            else:
                result = conn.execute(
                    text("SELECT * FROM payment_notifications WHERE landlord_id = :landlord_id ORDER BY created_at DESC"),
                    {"landlord_id": landlord_id}
                )
            notifications = []
            for row in result:
                notifications.append(self._row_to_payment_notification(row))
            return notifications
    
    def get_payment_notifications_by_bill(self, bill_id: str) -> List[PaymentNotification]:
        """Get all payment notifications for a bill"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM payment_notifications WHERE bill_id = :bill_id ORDER BY created_at DESC"),
                {"bill_id": bill_id}
            )
            notifications = []
            for row in result:
                notifications.append(self._row_to_payment_notification(row))
            return notifications
    
    def get_payment_notification_by_id(self, notification_id: str) -> Optional[PaymentNotification]:
        """Get payment notification by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM payment_notifications WHERE id = :id"),
                {"id": notification_id}
            )
            row = result.fetchone()
            if row:
                return self._row_to_payment_notification(row)
            return None
    
    def get_pending_notification_count(self, landlord_id: str) -> int:
        """Get count of pending payment notifications for a landlord"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) as count FROM payment_notifications WHERE landlord_id = :landlord_id AND status = 'pending'"),
                {"landlord_id": landlord_id}
            )
            row = result.fetchone()
            return row.count if row else 0
    
    def create_payment_notification(self, notification: PaymentNotification) -> PaymentNotification:
        """Create a new payment notification"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO payment_notifications (
                        id, bill_id, renter_id, landlord_id, amount, currency,
                        status, renter_note, landlord_note, created_at, confirmed_at
                    ) VALUES (
                        :id, :bill_id, :renter_id, :landlord_id, :amount, :currency,
                        :status, :renter_note, :landlord_note, :created_at, :confirmed_at
                    )
                """),
                {
                    "id": notification.id,
                    "bill_id": notification.bill_id,
                    "renter_id": notification.renter_id,
                    "landlord_id": notification.landlord_id,
                    "amount": notification.amount,
                    "currency": notification.currency or "RON",
                    "status": notification.status or "pending",
                    "renter_note": notification.renter_note,
                    "landlord_note": notification.landlord_note,
                    "created_at": notification.created_at or datetime.now().isoformat(),
                    "confirmed_at": notification.confirmed_at
                }
            )
            conn.commit()
        return notification
    
    def update_payment_notification(self, notification_id: str, updates: Dict[str, Any]) -> Optional[PaymentNotification]:
        """Update payment notification fields"""
        if not updates:
            return self.get_payment_notification_by_id(notification_id)
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE payment_notifications SET {set_clause} WHERE id = :notification_id"),
                {"notification_id": notification_id, **updates}
            )
            conn.commit()
        return self.get_payment_notification_by_id(notification_id)
    
    def _row_to_payment_notification(self, row) -> PaymentNotification:
        """Convert database row to PaymentNotification model"""
        return PaymentNotification(
            id=row.id,
            bill_id=row.bill_id,
            renter_id=row.renter_id,
            landlord_id=row.landlord_id,
            amount=float(row.amount) if row.amount else 0,
            currency=row.currency or "RON",
            status=row.status or "pending",
            renter_note=row.renter_note,
            landlord_note=row.landlord_note,
            created_at=row.created_at.isoformat() if row.created_at else None,
            confirmed_at=row.confirmed_at.isoformat() if row.confirmed_at else None
        )
    
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
                    "has_api": supplier.has_api,
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
                    "has_api": supplier.has_api,
                    "bill_type": supplier.bill_type or "utilities",
                    "extraction_pattern_supplier": supplier.extraction_pattern_supplier
                }
            )
            conn.commit()
        return supplier
    
    def delete_supplier(self, supplier_id: str) -> bool:
        """Delete supplier"""
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
                    extraction_pattern_supplier=getattr(row, 'extraction_pattern_supplier', None),
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
                    extraction_pattern_supplier=getattr(row, 'extraction_pattern_supplier', None),
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    def create_property_supplier(self, ps: PropertySupplier) -> PropertySupplier:
        """Create property-supplier relationship (upsert)"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO property_suppliers (
                        id, property_id, supplier_id, extraction_pattern_supplier, 
                        contract_id, direct_debit, created_at, updated_at
                    ) VALUES (
                        :id, :property_id, :supplier_id, :extraction_pattern_supplier,
                        :contract_id, :direct_debit, :created_at, :updated_at
                    )
                    ON CONFLICT (property_id, supplier_id) DO UPDATE SET
                        extraction_pattern_supplier = EXCLUDED.extraction_pattern_supplier,
                        contract_id = EXCLUDED.contract_id,
                        direct_debit = EXCLUDED.direct_debit,
                        updated_at = EXCLUDED.updated_at
                """),
                {
                    "id": ps.id,
                    "property_id": ps.property_id,
                    "supplier_id": ps.supplier_id,
                    "extraction_pattern_supplier": ps.extraction_pattern_supplier,
                    "contract_id": ps.contract_id,
                    "direct_debit": ps.direct_debit,
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
        
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        with self.engine.connect() as conn:
            conn.execute(
                text(f"UPDATE property_suppliers SET {set_clause} WHERE id = :ps_id"),
                {"ps_id": ps_id, **updates}
            )
            conn.commit()
            
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
                    extraction_pattern_supplier=getattr(row, 'extraction_pattern_supplier', None),
                    contract_id=row.contract_id,
                    direct_debit=bool(row.direct_debit),
                    created_at=row.created_at.isoformat() if row.created_at else None,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    # ==================== USER PREFERENCES ====================
    
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        import json
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM user_preferences WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            if row:
                # Parse property_order JSON if present
                property_order = None
                if hasattr(row, 'property_order') and row.property_order:
                    try:
                        property_order = json.loads(row.property_order) if isinstance(row.property_order, str) else row.property_order
                    except (json.JSONDecodeError, TypeError):
                        property_order = None
                
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
                    iban_eur=getattr(row, 'iban_eur', None),
                    iban_usd=getattr(row, 'iban_usd', None),
                    property_order=property_order,
                    updated_at=row.updated_at.isoformat() if row.updated_at else None
                )
            return None
    
    def create_user_preferences(self, prefs: UserPreferences) -> UserPreferences:
        """Create or update user preferences (upsert)"""
        import json
        
        # Serialize property_order to JSON string if present
        property_order_json = None
        if prefs.property_order:
            property_order_json = json.dumps(prefs.property_order)
        
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO user_preferences (
                        id, user_id, language, view_mode, rent_warning_days, rent_currency, bill_currency,
                        date_format, phone_number, landlord_name, personal_email, iban, iban_eur, iban_usd, property_order, updated_at
                    ) VALUES (
                        :id, :user_id, :language, :view_mode, :rent_warning_days, :rent_currency, :bill_currency,
                        :date_format, :phone_number, :landlord_name, :personal_email, :iban, :iban_eur, :iban_usd, :property_order, :updated_at
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        language = EXCLUDED.language,
                        view_mode = EXCLUDED.view_mode,
                        rent_warning_days = EXCLUDED.rent_warning_days,
                        rent_currency = EXCLUDED.rent_currency,
                        bill_currency = EXCLUDED.bill_currency,
                        date_format = EXCLUDED.date_format,
                        phone_number = EXCLUDED.phone_number,
                        landlord_name = EXCLUDED.landlord_name,
                        personal_email = EXCLUDED.personal_email,
                        iban = EXCLUDED.iban,
                        iban_eur = EXCLUDED.iban_eur,
                        iban_usd = EXCLUDED.iban_usd,
                        property_order = EXCLUDED.property_order,
                        updated_at = EXCLUDED.updated_at
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
                    "iban_eur": prefs.iban_eur,
                    "iban_usd": prefs.iban_usd,
                    "property_order": property_order_json,
                    "updated_at": datetime.now().isoformat()
                }
            )
            conn.commit()
        return prefs

