from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import List, Optional, Any, Dict
import logging

from app.auth import get_current_user, TokenData
from app.incarca_service import get_incarca_service, IncarcaService
from app.models import (
    SupplierMatch, BalanceRequest, BalanceResponse,
    PaymentRequest, TransactionResponse, SupplierInfo, ProductInfo,
    BillStatus, UserRole
)
from app.database import db
from app.paths import get_bill_pdf_path, bill_pdf_exists

# test codes
# Incercati cu aceste coduri de bare:
# Electrica:
# 289090285002903376999999999999000000002452
# Aquatim:
# 3010001095301048412814/01/2026000000102.70
# Apavital:
# 1000284901011000001973921000000238530116

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/utility", tags=["Utility Payments"])


def _get_actor_label(access: Dict[str, Any]) -> str:
    """Build a safe actor label for logs."""
    if access["mode"] == "renter":
        renter = access["renter"]
        return f"renter:{renter.id}"

    current_user = access["current_user"]
    return current_user.email


def _get_accessible_bill(access: Dict[str, Any], bill_id: str):
    """Fetch a bill and verify the current actor is allowed to use it."""
    bill = db.get_bill(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    prop = db.get_property(bill.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if access["mode"] == "landlord":
        current_user = access["current_user"]
        if prop.landlord_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        renter = access["renter"]
        if prop.id != renter.property_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if bill.renter_id not in (None, 'all', renter.id):
            raise HTTPException(status_code=403, detail="Access denied")

    return bill, prop


async def require_utility_access(
    current_user: Optional[TokenData] = Depends(get_current_user),
    renter_token: Optional[str] = Header(default=None, alias="X-Renter-Token"),
) -> Dict[str, Any]:
    """Allow utility access for authenticated landlords or for renters using their public access token."""
    if renter_token:
        renter = db.get_renter_by_token(renter_token)
        if not renter:
            raise HTTPException(status_code=401, detail="Invalid renter token")

        prop = db.get_property(renter.property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        return {
            "mode": "renter",
            "renter": renter,
            "property": prop,
            "current_user": None,
        }

    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if current_user.role not in [UserRole.LANDLORD, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Landlord access required")

    return {
        "mode": "landlord",
        "renter": None,
        "property": None,
        "current_user": current_user,
    }

@router.get("/match-barcode", response_model=List[SupplierMatch])
async def match_barcode(
    barcode: str = Query(..., description="Barcode extracted from utility bill PDF"),
    access: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Match barcode to utility supplier
    
    Used after PDF parsing to identify which utility company the bill belongs to.
    Returns list of matching suppliers with their payment configuration.
    """
    logger.info("%s matching barcode: %s", _get_actor_label(access), barcode)
    
    try:
        suppliers = await incarca.match_barcode(barcode)
        
        if not suppliers:
            raise HTTPException(
                status_code=404,
                detail="No utility supplier found for this barcode"
            )
        
        return suppliers
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in match_barcode: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/balance", response_model=BalanceResponse)
async def get_utility_balance(
    data: BalanceRequest,
    access: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Get balance for a utility bill
    
    Queries the utility provider to get the amount due for payment.
    Can be used by both landlords and renters.
    """
    logger.info("%s querying balance for supplier %s", _get_actor_label(access), data.supplierUid)
    
    try:
        balance = await incarca.get_balance(data)
        return balance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_utility_balance: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pay", response_model=TransactionResponse)
async def pay_utility_bill(
    data: PaymentRequest,
    access: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Execute utility bill payment
    
    Creates a transaction to pay the utility bill.
    Can be used by both landlords and renters.
    
    Note: This will charge the configured payment method.
    """
    logger.info(
        "%s initiating payment for supplier %s, amount: %s",
        _get_actor_label(access),
        data.supplierUid,
        data.amount,
    )
    
    try:
        bill = None
        if data.billId:
            bill, _ = _get_accessible_bill(access, data.billId)

        # If amount not provided, fetch balance first
        if data.amount is None:
            balance_request = BalanceRequest(
                supplierUid=data.supplierUid,
                productUid=data.productUid,
                paymentFields=data.paymentFields,
                transactionId=data.transactionId,
                partnerTransactionId=data.partnerTransactionId,
                terminalType=data.terminalType
            )
            balance_response = await incarca.get_balance(balance_request)
            data.amount = balance_response.balance
        
        # Execute payment
        transaction = await incarca.create_transaction(data)

        if bill and transaction.success and transaction.status not in {'failed', 'cancelled'}:
            bill.status = BillStatus.PAID
            db.save_bill(bill)
        
        # TODO: Record transaction in database for audit trail
        # await record_utility_payment(current_user.email, transaction)
        
        return transaction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in pay_utility_bill: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Supporting endpoints

@router.get("/suppliers", response_model=List[SupplierInfo])
async def list_suppliers(
    _: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """Get list of all available utility suppliers"""
    try:
        suppliers = await incarca.get_suppliers()
        return suppliers
    except Exception as e:
        logger.error(f"Error listing suppliers: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch suppliers")


@router.get("/suppliers/{supplier_uid}", response_model=SupplierInfo)
async def get_supplier_details(
    supplier_uid: str,
    _: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """Get details for a specific supplier"""
    try:
        supplier = await incarca.get_supplier(supplier_uid)
        return supplier
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier details")


@router.get("/suppliers/{supplier_uid}/products", response_model=List[ProductInfo])
async def get_supplier_products(
    supplier_uid: str,
    _: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """Get products for a specific supplier"""
    try:
        products = await incarca.get_supplier_products(supplier_uid)
        return products
    except Exception as e:
        logger.error(f"Error getting supplier products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@router.get("/products", response_model=List[ProductInfo])
async def list_products(
    _: Dict[str, Any] = Depends(require_utility_access),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """Get list of all available products"""
    try:
        products = await incarca.get_all_products()
        return products
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@router.get("/extract-barcode/{bill_id}")
async def extract_barcode_from_bill(
    bill_id: str,
    access: Dict[str, Any] = Depends(require_utility_access)
):
    """
    Extract barcode from a bill's PDF file.
    
    Uses pyzbar to detect and extract barcodes from the bill's PDF.
    Returns the primary barcode suitable for utility payment.
    """
    bill, prop = _get_accessible_bill(access, bill_id)
    landlord_id = prop.landlord_id
    
    # Check if PDF exists
    if not bill_pdf_exists(landlord_id, bill_id):
        raise HTTPException(status_code=404, detail="No PDF file found for this bill")
    
    # Get PDF path and read file
    pdf_path = get_bill_pdf_path(landlord_id, bill_id)
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
    except Exception as e:
        logger.error(f"Error reading PDF file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read PDF file")
    
    # Extract barcodes
    try:
        from app.utils.barcode_extractor import extract_barcodes_from_pdf, get_primary_barcode, is_barcode_extraction_available
        
        if not is_barcode_extraction_available():
            raise HTTPException(
                status_code=503, 
                detail="Barcode extraction not available - missing dependencies (pyzbar, pillow)"
            )
        
        # Get all barcodes
        all_barcodes = extract_barcodes_from_pdf(pdf_bytes)
        
        # Get the primary barcode
        primary_barcode = get_primary_barcode(pdf_bytes)
        
        return {
            "primary_barcode": primary_barcode,
            "all_barcodes": all_barcodes,
            "bill_id": bill_id,
            "bill_number": bill.bill_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting barcodes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract barcodes: {str(e)}")
