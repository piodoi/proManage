"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from app.routes import (
    auth_router,
    admin_router,
    properties_router,
    suppliers_router,
    renters_router,
    bills_router,
    renter_public_router,
    email_router,
    ebloc_router,
    sync_router,
)
from app.routes.subscription_routes import router as subscription_router
from app.routes import load_extraction_patterns_from_json

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="ProManage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(properties_router)
app.include_router(suppliers_router)
app.include_router(renters_router)
app.include_router(bills_router)
app.include_router(renter_public_router)
app.include_router(email_router)
app.include_router(ebloc_router)
app.include_router(sync_router)
app.include_router(subscription_router)


@app.on_event("startup")
async def startup_event():
    """Load extraction patterns from JSON files on startup."""
    load_extraction_patterns_from_json()


@app.get("/health")
async def health():
    return {"status": "ok"}
