"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta

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
    payment_notifications_router,
)
from app.routes.subscription_routes import router as subscription_router
from app.routes.text_pattern_routes import router as text_pattern_router
from app.routes.stripe_routes import router as stripe_router
from app.utils.suppliers import initialize_suppliers
from app.utils.currency import initialize_exchange_rates, shutdown_exchange_rates
from app.contract_expiry_checker import check_and_notify_expiring_contracts
from app.routes import incarca_routes


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

# Get frontend URL from env, with fallback for dev
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Build CORS origins list
cors_origins = [
    FRONTEND_URL,
    "http://localhost:5173",  # Dev
    "http://localhost:5174",  # Dev (alternate port)
]
# Add additional origins from env (comma-separated)
extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    cors_origins.extend([origin.strip() for origin in extra_origins.split(",") if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.lhr\.life",  # Allow all lhr.life subdomains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight for 24 hours (86400 seconds)
)

@app.middleware("http")
async def log_requests(request, call_next):
    #print(f"[DEBUG] {request.method} {request.url} - Host: {request.headers.get('host')}")
    response = await call_next(request)
    return response

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
app.include_router(stripe_router)
app.include_router(payment_notifications_router)
app.include_router(incarca_routes.router)



# Background task for contract expiry check
_scheduler_task = None
_scheduler_running = False


async def contract_expiry_scheduler():
    """Background task that runs contract expiry check daily at 8:00 AM."""
    global _scheduler_running
    _scheduler_running = True
    
    logger.info("[Scheduler] Contract expiry scheduler started")
    
    while _scheduler_running:
        try:
            # Calculate time until next 8:00 AM
            now = datetime.now()
            target_time = time(8, 0, 0)  # 8:00 AM
            
            if now.time() >= target_time:
                # Already past 8 AM today, schedule for tomorrow
                next_run = datetime.combine(now.date(), target_time) + timedelta(days=1)
            else:
                # Schedule for today
                next_run = datetime.combine(now.date(), target_time)
            
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"[Scheduler] Next contract expiry check in {wait_seconds/3600:.1f} hours")
            
            # Wait until next scheduled time
            await asyncio.sleep(wait_seconds)
            
            if not _scheduler_running:
                break
            
            # Run the contract expiry check
            logger.info("[Scheduler] Running scheduled contract expiry check...")
            try:
                result = await check_and_notify_expiring_contracts()
                logger.info(f"[Scheduler] Contract expiry check complete: {result}")
            except Exception as e:
                logger.error(f"[Scheduler] Contract expiry check failed: {e}")
            
        except asyncio.CancelledError:
            logger.info("[Scheduler] Contract expiry scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"[Scheduler] Scheduler error: {e}")
            # Wait a bit before retrying
            await asyncio.sleep(60)
    
    logger.info("[Scheduler] Contract expiry scheduler stopped")


@app.on_event("startup")
async def startup_event():
    """Initialize suppliers and exchange rates on startup."""
    global _scheduler_task
    initialize_suppliers()
    
    # Initialize exchange rates (fetch immediately so they're available for all users)
    await initialize_exchange_rates()
    logger.info("[Startup] Exchange rates initialized")
    
    # Start the contract expiry scheduler
    _scheduler_task = asyncio.create_task(contract_expiry_scheduler())
    logger.info("[Startup] Contract expiry scheduler task created")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _scheduler_running, _scheduler_task
    
    logger.info("Shutting down application...")
    
    # Stop the scheduler
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    
    # Stop exchange rate background refresh
    await shutdown_exchange_rates()
    
    # Give connections time to close gracefully
    await asyncio.sleep(0.1)


@app.get("/health")
async def health():
    return {"status": "ok"}
