import os
import logging
import secrets
import time
from collections import defaultdict
from pydantic import BaseModel, EmailStr
import bcrypt
import httpx

from fastapi import APIRouter, HTTPException, Depends, Request

from app.models import User, UserRole, OAuthProvider
from app.auth import create_access_token, require_auth
from app.database import db, has_any_admin

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ConfirmEmailRequest(BaseModel):
    token: str


rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10

email_confirmation_tokens: dict[str, dict] = {}
EMAIL_CONFIRMATION_EXPIRY = 3600


def check_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded rate limit. Returns True if allowed, False if blocked."""
    now = time.time()
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    rate_limit_store[ip].append(now)
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash using bcrypt directly."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def generate_confirmation_token() -> str:
    """Generate a secure random token for email confirmation."""
    return secrets.token_urlsafe(32)


@router.get("/has-admin")
async def check_has_admin():
    """Check if any admin user exists. Used by frontend to hide demo mode."""
    return {"has_admin": has_any_admin()}


@router.post("/register")
async def auth_register(data: RegisterRequest, request: Request):
    """Register a new user with email and password."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        logger.warning(f"[Auth] Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    logger.info(f"[Auth] Registration attempt for email: {data.email}")
    
    existing = next((u for u in db.list_users() if u.email == data.email), None)
    if existing:
        logger.warning(f"[Auth] Registration failed - email already exists: {data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    hashed = hash_password(data.password)
    role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
    
    confirmation_token = generate_confirmation_token()
    email_confirmation_tokens[confirmation_token] = {
        "email": data.email,
        "name": data.name,
        "password_hash": hashed,
        "role": role,
        "created_at": time.time(),
    }
    
    logger.info(f"[Auth] Email confirmation token generated for: {data.email}")
    logger.info(f"[Auth] Confirmation token (dev mode): {confirmation_token}")
    
    return {
        "message": "Please check your email to confirm your account",
        "confirmation_token": confirmation_token,
    }


@router.post("/confirm-email")
async def confirm_email(data: ConfirmEmailRequest, request: Request):
    """Confirm email and create user account."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    token_data = email_confirmation_tokens.get(data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token")
    
    if time.time() - token_data["created_at"] > EMAIL_CONFIRMATION_EXPIRY:
        del email_confirmation_tokens[data.token]
        raise HTTPException(status_code=400, detail="Confirmation token has expired")
    
    existing = next((u for u in db.list_users() if u.email == token_data["email"]), None)
    if existing:
        del email_confirmation_tokens[data.token]
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = UserRole.ADMIN if not has_any_admin() else token_data["role"]
    
    user = User(
        email=token_data["email"],
        name=token_data["name"],
        role=role,
        password_hash=token_data["password_hash"],
    )
    db.save_user(user)
    
    del email_confirmation_tokens[data.token]
    
    logger.info(f"[Auth] User confirmed and created: {user.email}, role: {role.value}")
    
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/login")
async def auth_login(data: LoginRequest, request: Request):
    """Login with email and password."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        logger.warning(f"[Auth] Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    logger.info(f"[Auth] Login attempt for email: {data.email}")
    
    user = next((u for u in db.list_users() if u.email == data.email), None)
    if not user:
        logger.warning(f"[Auth] Login failed - user not found: {data.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.password_hash:
        logger.warning(f"[Auth] Login failed - no password set (OAuth user): {data.email}")
        raise HTTPException(status_code=401, detail="This account uses OAuth login (Google/Facebook)")
    
    if not verify_password(data.password, user.password_hash):
        logger.warning(f"[Auth] Login failed - invalid password: {data.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    logger.info(f"[Auth] Login successful: {data.email}")
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/google")
async def auth_google(id_token: str, request: Request):
    """Authenticate with Google OAuth."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    logger.info("[Auth] Google OAuth attempt")
    
    if not GOOGLE_CLIENT_ID:
        logger.error("[Auth] Google OAuth not configured - GOOGLE_CLIENT_ID missing")
        raise HTTPException(status_code=500, detail="Google OAuth not configured on server")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if resp.status_code != 200:
            logger.error(f"[Auth] Google token validation failed: {resp.status_code}")
            raise HTTPException(status_code=401, detail="Invalid Google token")
        data = resp.json()
    
    if data.get("aud") != GOOGLE_CLIENT_ID:
        logger.error("[Auth] Google token audience mismatch")
        raise HTTPException(status_code=401, detail="Token not issued for this application")
    
    email = data.get("email")
    name = data.get("name", email)
    oauth_id = data.get("sub")
    
    logger.info(f"[Auth] Google OAuth validated for email: {email}")
    
    user = next(
        (u for u in db.list_users() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.GOOGLE),
        None,
    )
    if not user:
        role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
        user = User(
            email=email,
            name=name,
            role=role,
            oauth_provider=OAuthProvider.GOOGLE,
            oauth_id=oauth_id,
        )
        db.save_user(user)
        logger.info(f"[Auth] New Google user created: {email}, role: {role.value}")
    
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/facebook")
async def auth_facebook(token: str, request: Request):
    """Authenticate with Facebook OAuth."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}")
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Facebook token")
        data = resp.json()
    
    email = data.get("email")
    name = data.get("name", email)
    oauth_id = data.get("id")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Facebook")
    
    user = next(
        (u for u in db.list_users() if u.oauth_id == oauth_id and u.oauth_provider == OAuthProvider.FACEBOOK),
        None,
    )
    if not user:
        role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
        user = User(
            email=email,
            name=name,
            role=role,
            oauth_provider=OAuthProvider.FACEBOOK,
            oauth_id=oauth_id,
        )
        db.save_user(user)
    
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me")
async def get_me(current_user=Depends(require_auth)):
    """Get current user info."""
    user = db.get_user(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/demo")
async def auth_demo(email: str, name: str, request: Request):
    """Demo login for testing (creates a landlord user)."""
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute.")
    
    user = next((u for u in db.list_users() if u.email == email), None)
    if not user:
        role = UserRole.ADMIN if not has_any_admin() else UserRole.LANDLORD
        user = User(email=email, name=name, role=role)
        db.save_user(user)
    
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
