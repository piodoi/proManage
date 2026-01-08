"""Sync routes for email and rent bill synchronization."""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.models import TokenData
from app.auth import require_landlord
from app.database import db


def get_default_bill_currency(user_id: str) -> str:
    """Get default bill currency from user preferences, or return 'RON' as fallback."""
    preferences = db.get_user_preferences(user_id)
    if preferences and preferences.bill_currency:
        return preferences.bill_currency
    return "RON"


router = APIRouter(tags=["sync"])
logger = logging.getLogger(__name__)


def resolve_supplier_id(
    property_id: str,
    supplier_name: Optional[str] = None,
    extraction_pattern_id: Optional[str] = None,
    contract_id: Optional[str] = None
) -> Optional[str]:
    """
    Resolve the supplier_id for a bill based on available information.
    
    Tries in order:
    1. Match by contract_id against PropertySupplier for this property
    2. Match by supplier name against PropertySupplier for this property
    3. Match by extraction_pattern_id -> pattern.supplier -> Supplier
    
    Returns:
        supplier_id if found, None otherwise
    """
    # Get all property suppliers for this property
    property_suppliers = db.list_property_suppliers(property_id)
    
    # Get all suppliers for matching
    all_suppliers = db.list_suppliers()
    
    # FIRST: Try to match by extraction_pattern_id (text pattern name like "engie")
    if extraction_pattern_id:
        for s in all_suppliers:
            if s.extraction_pattern_supplier and s.extraction_pattern_supplier == extraction_pattern_id:
                # Check if this supplier is linked to the property
                ps_match = next((ps for ps in property_suppliers if ps.supplier_id == s.id), None)
                if ps_match:
                    return s.id
    
    # SECOND: Try to match by contract_id
    if contract_id:
        for ps in property_suppliers:
            if ps.contract_id and ps.contract_id == contract_id:
                return ps.supplier_id
    
    # THIRD: Try to match by supplier name from extraction pattern
    if supplier_name:
        for s in all_suppliers:
            if s.name.lower() == supplier_name.lower():
                # Check if this supplier is linked to the property
                ps_match = next((ps for ps in property_suppliers if ps.supplier_id == s.id), None)
                if ps_match:
                    return s.id
    
    # Log detailed error only when no match is found
    supplier_names = [s.name for s in all_suppliers]
    extraction_patterns = [(s.name, s.extraction_pattern_supplier) for s in all_suppliers if s.extraction_pattern_supplier]
    property_supplier_contracts = [(ps.supplier_id, ps.contract_id) for ps in property_suppliers if ps.contract_id]
    
    logger.warning(
        f"[Supplier Resolver] Failed to match supplier for property {property_id}\n"
        f"  Searched for: extraction_pattern_id='{extraction_pattern_id}', supplier_name='{supplier_name}', contract_id='{contract_id}'\n"
        f"  Available suppliers: {supplier_names}\n"
        f"  Extraction patterns: {extraction_patterns}\n"
        f"  Property suppliers with contracts: {property_supplier_contracts}"
    )
    return None


@router.post("/rent/generate")
async def generate_rent_bills(current_user: TokenData = Depends(require_landlord)):
    """
    Generate rent bills for all properties with renters who have rent_amount_eur set.
    Only generates bills for properties owned by the current user.
    """
    from app.models import Bill, BillType
    from calendar import monthrange
    
    logger.info(f"[Rent Bills] Generating rent bills for user {current_user.user_id}")
    
    # Get all properties for this user
    properties = db.list_properties(landlord_id=current_user.user_id)
    
    # Get user preferences for defaults
    preferences = db.get_user_preferences(current_user.user_id)
    default_currency = preferences.rent_currency if preferences and preferences.rent_currency else "EUR"
    warning_days = preferences.rent_warning_days if preferences and preferences.rent_warning_days else 5
    default_iban = preferences.iban if preferences and preferences.iban else None
    
    bills_created = 0
    errors = []
    
    for prop in properties:
        try:
            # Get all renters for this property
            renters = db.list_renters(prop.id)
            
            # Filter for renters with rent amount set
            renters_with_rent = [r for r in renters if r.rent_amount_eur and r.rent_amount_eur > 0]
            
            if not renters_with_rent:
                logger.debug(f"[Rent Bills] Property {prop.id} has no renters with rent_amount_eur set, skipping")
                continue
            
            # For each renter with rent, generate a rent bill
            for renter in renters_with_rent:
                # Calculate due date
                now = datetime.utcnow()
                
                # Calculate next month
                if now.month == 12:
                    next_year = now.year + 1
                    next_month = 1
                else:
                    next_year = now.year
                    next_month = now.month + 1
                
                # Use rent_day if specified, otherwise use 1st + warning_days
                if renter.rent_day and 1 <= renter.rent_day <= 28:
                    due_date = datetime(next_year, next_month, renter.rent_day, 0, 0, 0)
                else:
                    # Default: 1st of month + warning_days
                    from datetime import timedelta
                    warning_offset = max(0, warning_days - 1)
                    due_date = datetime(next_year, next_month, 1, 0, 0, 0) + timedelta(days=warning_offset)
                
                # Create bill with month number as bill_number
                bill_number = f"{next_month:02d}"  # Month number: 01-12
                
                # Check if a similar bill already exists for this month
                existing_bills = db.list_bills(property_id=prop.id)
                month_year_str = f"{next_year}-{next_month:02d}"
                duplicate_found = False
                
                for existing_bill in existing_bills:
                    if (existing_bill.renter_id == renter.id and 
                        existing_bill.bill_type == BillType.RENT and
                        existing_bill.due_date and
                        existing_bill.due_date.strftime("%Y-%m") == month_year_str):
                        duplicate_found = True
                        logger.debug(
                            f"[Rent Bills] Rent bill already exists for property {prop.id}, "
                            f"renter {renter.id}, month {month_year_str}"
                        )
                        break
                
                if duplicate_found:
                    continue
                
                # Create the bill
                # Format month name
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                month_name = month_names[next_month]
                
                bill = Bill(
                    property_id=prop.id,
                    renter_id=renter.id,
                    bill_type=BillType.RENT,
                    description=f"{month_name} {next_year}",
                    amount=renter.rent_amount_eur,
                    currency=default_currency,
                    due_date=due_date,
                    iban=default_iban,
                    bill_number=bill_number,
                    supplier_id=None,
                )
                
                db.save_bill(bill)
                bills_created += 1
                logger.info(
                    f"[Rent Bills] Created rent bill for property {prop.id}, "
                    f"renter {renter.id}, amount {renter.rent_amount_eur} {default_currency}, "
                    f"due {due_date.strftime('%Y-%m-%d')}"
                )
                
        except Exception as e:
            error_msg = f"Error generating rent bills for property {prop.id}: {str(e)}"
            logger.error(f"[Rent Bills] {error_msg}")
            errors.append(error_msg)
    
    logger.info(f"[Rent Bills] Generation complete. Created {bills_created} bills, {len(errors)} errors")
    
    return {
        "bills_created": bills_created,
        "errors": errors,
    }
