"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import asyncio
import sys

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
    preferences_router,
)
from app.routes.subscription_routes import router as subscription_router
from app.routes.text_pattern_routes import router as text_pattern_router
from app.utils.suppliers import initialize_suppliers

load_dotenv()

# Log database configuration
import os
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./promanage.db")
DB_TYPE = "SQLite" if DATABASE_URL.startswith("sqlite") else \
          "MySQL" if DATABASE_URL.startswith("mysql") else \
          "PostgreSQL" if DATABASE_URL.startswith("postgresql") else "Unknown"
print(f"[Database] Using {DB_TYPE} database")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Override any existing configuration
)

# Suppress harmless Windows asyncio connection cleanup errors
# These occur when clients close connections before server cleanup completes
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Ensure uvicorn access logs are shown
logging.getLogger('uvicorn.access').setLevel(logging.INFO)
logging.getLogger('uvicorn.error').setLevel(logging.INFO)

# Ensure all our loggers are set to INFO level
logging.getLogger('app').setLevel(logging.INFO)
logging.getLogger('app.routes').setLevel(logging.INFO)
logging.getLogger('app.web_scraper').setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="ProManage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Dev
        "http://localhost:5174",  # Dev (alternate port)
        "https://ultramic.ro",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # ← Cache preflight for 24 hours (86400 seconds)
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
app.include_router(preferences_router)
app.include_router(text_pattern_router)


@app.on_event("startup")
async def startup_event():
    """Initialize suppliers from JSON files on startup."""
    initialize_suppliers()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application...")
    # Give connections time to close gracefully
    await asyncio.sleep(0.1)


@app.get("/health")
async def health():
    return {"status": "ok"}
