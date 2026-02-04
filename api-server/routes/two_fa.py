"""
Two-Factor Authentication Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from models.database import get_db, User, SuperAdmin, Company
from services.two_factor_auth import TwoFactorAuth
from passlib.context import CryptContext
from jose import jwt, JWTError
import os

from utils.auth_helpers import (
    create_tokens_for_user,
    create_tokens_for_super_admin,
    get_current_user_from_request,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

router = APIRouter(prefix="/2fa", tags=["Two-Factor Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")


# ========== Request/Response Models ==========

class Setup2FAResponse(BaseModel):
    secret: str
    qr_code: str
    manual_entry_key: str

class Verify2FARequest(BaseModel):
    code: str

class Verify2FALoginRequest(BaseModel):
    user_id: int
    user_type: str
    code: str

class Disable2FARequest(BaseModel):
    password: str

class ResetUser2FARequest(BaseModel):
    user_id: int


# ========== Helper Functions ==========

def get_current_user(request: Request = None, authorization: str = Header(None), db: Session = Depends(get_db)):
    """Extract and validate user from JWT token (cookie or header)"""
    token = None

    # Try cookie first (frontend)
    if request:
        token = request.cookies.get("access_token")

    # Fallback to Authorization header (agent or legacy)
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        user_type = payload.get("type")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        if user_type == "super_admin":
            user = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
        else:
            user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user, user_type

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ========== 2FA Setup Endpoints ==========

@router.post("/setup", response_model=Setup2FAResponse)
async def setup_2fa(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Initialize 2FA setup for a user.
    Returns QR code and secret for authenticator app.
    """
    user, user_type = get_current_user(request, authorization, db)
    
    if getattr(user, 'totp_enabled', False):
        raise HTTPException(status_code=400, detail="2FA is already enabled. Disable it first to reconfigure.")
    
    secret = TwoFactorAuth.generate_secret()
    
    user.totp_secret = secret
    user.totp_enabled = False
    db.commit()
    
    qr_code = TwoFactorAuth.generate_qr_code(secret, user.email)
    
    return Setup2FAResponse(
        secret=secret,
        qr_code=qr_code,
        manual_entry_key=secret
    )


@router.post("/verify-setup")
async def verify_2fa_setup(
    request: Verify2FARequest,
    req: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Verify the TOTP code to complete 2FA setup."""
    user, user_type = get_current_user(req, authorization, db)
    
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /2fa/setup first.")
    
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled.")
    
    if not TwoFactorAuth.verify_totp(user.totp_secret, request.code):
        raise HTTPException(status_code=400, detail="Invalid verification code. Please try again.")
    
    user.totp_enabled = True
    db.commit()
    
    return {"success": True, "message": "2FA has been enabled successfully."}


# ========== 2FA Login Verification ==========

@router.post("/verify-login")
async def verify_2fa_login(
    request: Verify2FALoginRequest,
    req: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Verify 2FA code during login."""
    if request.user_type == "super_admin":
        user = db.query(SuperAdmin).filter(SuperAdmin.id == request.user_id).first()
    else:
        user = db.query(User).filter(User.id == request.user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA is not enabled for this user")
    
    if not TwoFactorAuth.verify_totp(user.totp_secret, request.code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    user.last_login_at = datetime.utcnow()
    db.commit()

    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("User-Agent")

    if request.user_type == "super_admin":
        # Super admin: access token only (no refresh - security)
        access_token = create_tokens_for_super_admin(user)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600,  # 1 hour for super admin
            path="/"
        )

        return {
            "success": True,
            "type": "super_admin",
            "user_id": user.id,
            "company_id": None
        }
    else:
        # Regular user: access + refresh tokens
        access_token, refresh_token, session_id = create_tokens_for_user(
            db=db,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/api/auth"
        )

        return {
            "success": True,
            "type": user.role if user.role else "user",
            "user_id": user.id,
            "company_id": user.company_id
        }


# ========== 2FA Management ==========

@router.post("/disable")
async def disable_2fa(
    request: Disable2FARequest,
    req: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Disable 2FA for the current user."""
    user, user_type = get_current_user(req, authorization, db)
    
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    user.totp_enabled = False
    user.totp_secret = None
    db.commit()
    
    return {"success": True, "message": "2FA has been disabled."}


@router.get("/status")
async def get_2fa_status(
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get current 2FA status for the user"""
    user, user_type = get_current_user(request, authorization, db)
    
    return {
        "enabled": getattr(user, 'totp_enabled', False),
        "user_type": user_type
    }


# ========== Admin Functions ==========

@router.post("/reset-user")
async def reset_user_2fa(
    request: ResetUser2FARequest,
    req: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Reset 2FA for another user (admin function)."""
    current_user, current_type = get_current_user(req, authorization, db)
    
    target_user = db.query(User).filter(User.id == request.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_type == "super_admin":
        pass  # Super admin can reset anyone
    elif current_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="You can only reset 2FA for users in your company")
        if target_user.role == "admin" and target_user.id != current_user.id:
            raise HTTPException(status_code=403, detail="You cannot reset 2FA for other admins")
    else:
        raise HTTPException(status_code=403, detail="You don't have permission to reset 2FA for other users")
    
    target_user.totp_enabled = False
    target_user.totp_secret = None
    db.commit()
    
    return {"success": True, "message": f"2FA has been reset for {target_user.email}"}


@router.post("/enforce-company")
async def set_company_2fa_enforcement(
    enforce: bool,
    request: Request,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Set whether 2FA is mandatory for all users in the company."""
    current_user, current_type = get_current_user(request, authorization, db)
    
    if current_type not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can change this setting")
    
    if current_type == "super_admin":
        raise HTTPException(status_code=400, detail="Super admins don't belong to a company")
    
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.require_2fa = enforce
    db.commit()
    
    return {"success": True, "require_2fa": enforce}
