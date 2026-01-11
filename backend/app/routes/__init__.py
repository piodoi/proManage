from app.routes.auth_routes import router as auth_router
from app.routes.admin_routes import router as admin_router
from app.routes.properties_routes import router as properties_router
from app.routes.suppliers_routes import router as suppliers_router
from app.routes.renters_routes import router as renters_router
from app.routes.bills_routes import router as bills_router
from app.routes.renter_public_routes import router as renter_public_router
from app.routes.email_routes import router as email_router
from app.routes.ebloc_routes import router as ebloc_router
from app.routes.sync_routes import router as sync_router
from app.routes.preferences_routes import router as preferences_router

__all__ = [
    "auth_router",
    "admin_router",
    "properties_router",
    "suppliers_router",
    "renters_router",
    "bills_router",
    "renter_public_router",
    "email_router",
    "ebloc_router",
    "sync_router",
    "preferences_router",
]
