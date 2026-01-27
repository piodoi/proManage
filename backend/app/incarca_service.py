import httpx
import base64
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException
import os
import uuid

from app.models import (
    SupplierMatch, BalanceRequest, BalanceResponse, 
    PaymentRequest, TransactionResponse, SupplierInfo, ProductInfo
)

logger = logging.getLogger(__name__)

class IncarcaService:
    """Service for INCARCA REST API integration - Utility Bill Payments"""
    
    def __init__(self):
        self.base_url = os.getenv(
            "INCARCA_BASE_URL", 
            "https://incarcawebapi-mdstage.evozon.com/incarca"
        )
        self.client_id = os.getenv("INCARCA_CLIENT_ID")
        self.client_secret = os.getenv("INCARCA_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            logger.warning("INCARCA credentials not configured in environment")
        
        self.token = None
        self.token_expires = None
        self._http_client = None
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-loaded HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _encode_credentials(self) -> str:
        """Encode client credentials to base64 for Basic Auth"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return encoded
    
    async def get_token(self) -> str:
        """
        Get OAuth2 token (with caching and auto-refresh)
        Returns the Bearer token string
        """
        # Check if token is still valid
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token
        
        # Request new token
        try:
            url = f"{self.base_url}/oauth/token"
            headers = {
                "Authorization": f"Basic {self._encode_credentials()}",
                "Content-Type": "application/json"
            }
            params = {"grant_type": "client_credentials"}
            
            response = await self.http_client.post(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)  # Default 1 hour
            
            # Set expiration with 5-minute buffer
            self.token_expires = datetime.now() + timedelta(seconds=expires_in - 300)
            
            logger.info("Successfully obtained OAuth2 token from INCARCA API")
            return self.token
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to obtain OAuth2 token: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to authenticate with payment provider"
            )
        except Exception as e:
            logger.error(f"Error obtaining OAuth2 token: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail="Payment service authentication error"
            )
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with Bearer token for API requests"""
        token = await self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def match_barcode(self, barcode: str) -> List[SupplierMatch]:
        """
        Identify supplier from barcode extracted from PDF
        
        Args:
            barcode: Barcode string from utility bill PDF
            
        Returns:
            List of matching suppliers with payment configuration
        """
        try:
            url = f"{self.base_url}/webapi/v2/transactions/utility/match-barcode"
            headers = await self._get_headers()
            params = {"barcode": barcode}
            
            response = await self.http_client.get(url, headers=headers, params=params)

            logger.info(f"Matched barcode response {response} recieved.")

            response.raise_for_status()
            
            data = response.json()
            # Parse response into SupplierMatch models
            suppliers = [SupplierMatch(**item) for item in data]
            
            logger.info(f"Matched barcode to {len(suppliers)} supplier(s)")
            return suppliers
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Barcode match failed: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                return []  # No matches found
            raise HTTPException(
                status_code=500,
                detail="Failed to match barcode with utility provider"
            )
        except Exception as e:
            logger.error(f"Error matching barcode: {str(e)}")
            raise HTTPException(status_code=500, detail="Barcode matching error")
    
    async def get_balance(self, request: BalanceRequest) -> BalanceResponse:
        """
        Get utility bill balance (amount to pay)
        
        Args:
            request: BalanceRequest with supplier and payment field data
            
        Returns:
            BalanceResponse with amount and bill details
        """
        try:
            url = f"{self.base_url}/webapi/v2/transactions/utility/balance"
            headers = await self._get_headers()
            
            # Generate transaction ID if not provided
            if not request.transactionId:
                request.transactionId = str(uuid.uuid4())
            
            payload = request.dict(exclude_none=True)
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            balance_response = BalanceResponse(
                balance=data.get("balance", 0.0),
                currency=data.get("currency", "RON"),
                utilityData=data.get("utilityData"),
                success=True
            )
            
            logger.info(f"Retrieved balance: {balance_response.balance} {balance_response.currency}")
            return balance_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Balance query failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve bill balance"
            )
        except Exception as e:
            logger.error(f"Error retrieving balance: {str(e)}")
            raise HTTPException(status_code=500, detail="Balance query error")
    
    async def create_transaction(self, request: PaymentRequest) -> TransactionResponse:
        """
        Execute utility bill payment transaction
        
        Args:
            request: PaymentRequest with supplier, amount, and payment fields
            
        Returns:
            TransactionResponse with transaction details and status
        """
        try:
            url = f"{self.base_url}/webapi/v2/transactions/utility"
            headers = await self._get_headers()
            
            # Generate transaction ID if not provided
            if not request.transactionId:
                request.transactionId = str(uuid.uuid4())
            
            payload = request.dict(exclude_none=True)
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            transaction_response = TransactionResponse(
                transactionId=data.get("transactionId", request.transactionId),
                status=data.get("status", "completed"),
                amount=data.get("amount", request.amount),
                currency=data.get("currency", "RON"),
                timestamp=datetime.now(),
                receiptData=data.get("receiptData"),
                success=True,
                message=data.get("message")
            )
            
            logger.info(f"Transaction created: {transaction_response.transactionId} - Status: {transaction_response.status}")
            return transaction_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Transaction failed: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"Payment transaction failed: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error creating transaction: {str(e)}")
            raise HTTPException(status_code=500, detail="Transaction creation error")
    
    # Supporting endpoints
    
    async def get_suppliers(self) -> List[SupplierInfo]:
        """Get list of all available suppliers"""
        try:
            url = f"{self.base_url}/webapi/v2/suppliers"
            headers = await self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            suppliers = [SupplierInfo(**item) for item in data]
            
            return suppliers
            
        except Exception as e:
            logger.error(f"Error fetching suppliers: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch suppliers")
    
    async def get_supplier(self, supplier_uid: str) -> SupplierInfo:
        """Get details for a specific supplier"""
        try:
            url = f"{self.base_url}/webapi/v2/suppliers/{supplier_uid}"
            headers = await self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return SupplierInfo(**data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Supplier not found")
            raise HTTPException(status_code=500, detail="Failed to fetch supplier details")
    
    async def get_supplier_products(self, supplier_uid: str) -> List[ProductInfo]:
        """Get products for a specific supplier"""
        try:
            url = f"{self.base_url}/webapi/v2/suppliers/{supplier_uid}/products"
            headers = await self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            products = [ProductInfo(**item) for item in data]
            
            return products
            
        except Exception as e:
            logger.error(f"Error fetching supplier products: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch products")
    
    async def get_all_products(self) -> List[ProductInfo]:
        """Get list of all available products"""
        try:
            url = f"{self.base_url}/webapi/v2/products"
            headers = await self._get_headers()
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            products = [ProductInfo(**item) for item in data]
            
            return products
            
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch products")


# Singleton instance
_incarca_service: Optional[IncarcaService] = None

def get_incarca_service() -> IncarcaService:
    """Get or create IncarcaService singleton instance"""
    global _incarca_service
    if _incarca_service is None:
        _incarca_service = IncarcaService()
    return _incarca_service
