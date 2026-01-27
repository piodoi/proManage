from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
import logging

from app.auth import require_landlord, TokenData
from app.incarca_service import get_incarca_service, IncarcaService
from app.models import (
    SupplierMatch, BalanceRequest, BalanceResponse,
    PaymentRequest, TransactionResponse, SupplierInfo, ProductInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/utility", tags=["Utility Payments"])

@router.post("/match-barcode", response_model=List[SupplierMatch])
async def match_barcode(
    barcode: str = Query(..., description="Barcode extracted from utility bill PDF"),
    current_user: TokenData = Depends(require_landlord),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Match barcode to utility supplier
    
    Used after PDF parsing to identify which utility company the bill belongs to.
    Returns list of matching suppliers with their payment configuration.
    """
    logger.info(f"User {current_user.email} matching barcode: {barcode}")
    
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
    current_user: TokenData = Depends(require_landlord),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Get balance for a utility bill
    
    Queries the utility provider to get the amount due for payment.
    Can be used by both landlords and renters.
    """
    logger.info(f"User {current_user.email} querying balance for supplier {data.supplierUid}")
    
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
    current_user: TokenData = Depends(require_landlord),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """
    Execute utility bill payment
    
    Creates a transaction to pay the utility bill.
    Can be used by both landlords and renters.
    
    Note: This will charge the configured payment method.
    """
    logger.info(f"User {current_user.email} initiating payment for supplier {data.supplierUid}, amount: {data.amount}")
    
    try:
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
    current_user: TokenData = Depends(require_landlord),
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
    current_user: TokenData = Depends(require_landlord),
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
    current_user: TokenData = Depends(require_landlord),
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
    current_user: TokenData = Depends(require_landlord),
    incarca: IncarcaService = Depends(get_incarca_service)
):
    """Get list of all available products"""
    try:
        products = await incarca.get_all_products()
        return products
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")
