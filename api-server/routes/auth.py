from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.database import get_db, SuperAdmin, User, Company, Product, CompanyProductSubscription, Project, EmailVerificationRateLimit
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import os
import secrets
import hashlib
from pydantic import BaseModel
from typing import Optional
from utils.auth_helpers import (
    create_tokens_for_user,
    create_tokens_for_super_admin,
    validate_refresh_token,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    check_rate_limit,
    log_login_attempt,
    revoke_session,
    revoke_all_sessions,
    increment_token_version,
    get_user_sessions,
    get_current_user_from_request,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest, req: Request, response: Response, db: Session = Depends(get_db)):
    email = request.email.lower().strip()
    password = request.password
    ip_address = req.client.host if req.client else None
    user_agent = req.headers.get("User-Agent")

    # Check rate limit BEFORE any authentication
    check_rate_limit(db, email, ip_address)

    # Check super admin
    admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
    if admin and pwd_context.verify(password, admin.password_hash):
        # Check if 2FA is enabled
        if getattr(admin, 'totp_enabled', False):
            return {
                "requires_2fa": True,
                "user_id": admin.id,
                "type": "super_admin"
            }

        admin.last_login_at = datetime.utcnow()
        db.commit()

        # Log successful attempt
        log_login_attempt(db, email, ip_address, success=True)

        # Notify product owner about super admin login
        from services.email_service import notify_super_admin_login
        notify_super_admin_login(ip_address=ip_address)

        # Super admin must set up 2FA if not enabled
        # Create access token only (no refresh for super admin - security)
        access_token = create_tokens_for_super_admin(admin)

        # Set HttpOnly cookie
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
            "requires_2fa": False,
            "requires_2fa_setup": True,
            "type": "super_admin",
            "user_id": admin.id,
            "company_id": None
        }
    
    # Check regular user
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):

        # Check if email is verified
        if not getattr(user, 'is_verified', True):  # Default True for legacy users
            raise HTTPException(
                status_code=403,
                detail="Email not verified",
                headers={"X-Error-Code": "EMAIL_NOT_VERIFIED"}
            )

        user_type = user.role if user.role else "user"
        
        # Check if 2FA is enabled
        if getattr(user, 'totp_enabled', False):
            return {
                "requires_2fa": True,
                "user_id": user.id,
                "type": user_type,
                "company_id": user.company_id
            }
        
        # Check if 2FA setup is required (for admins or enforced companies)
        requires_2fa_setup = False
        
        if user_type == "admin" and not getattr(user, 'totp_enabled', False):
            requires_2fa_setup = True

        company = db.query(Company).filter(Company.id == user.company_id).first() if user.company_id else None
        if not requires_2fa_setup and company:
            if getattr(company, 'require_2fa', False) and not getattr(user, 'totp_enabled', False):
                requires_2fa_setup = True
        
        user.last_login_at = datetime.utcnow()
        db.commit()

        # Log successful attempt
        log_login_attempt(db, email, ip_address, success=True)

        # Create access and refresh tokens
        access_token, refresh_token, session_id = create_tokens_for_user(
            db=db,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Set HttpOnly cookies
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
            path="/api/auth"  # Only sent to auth endpoints
        )

        return {
            "requires_2fa": False,
            "requires_2fa_setup": requires_2fa_setup,
            "type": user_type,
            "user_id": user.id,
            "company_id": user.company_id,
            "onboarding_completed": getattr(company, 'onboarding_completed', True) if company else True
        }

    # Log failed attempt
    log_login_attempt(db, email, ip_address, success=False)
    raise HTTPException(status_code=401, detail="Invalid credentials")

def create_token(data: dict):
    """
    DEPRECATED: Use create_tokens_for_user or create_tokens_for_super_admin instead.
    Kept for backward compatibility with 2FA flow (will be updated).
    """
    to_encode = data.copy()
    if data.get("type") == "super_admin":
        expire = datetime.utcnow() + timedelta(hours=1)
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    #expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


# ========== SESSION MANAGEMENT ENDPOINTS ==========

@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Logout current session. Clears cookies and revokes session.
    """
    refresh_token = request.cookies.get("refresh_token")

    if refresh_token:
        try:
            from jose import jwt
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])
            session_id = payload.get("session_id")
            user_id = payload.get("user_id")
            if session_id and user_id:
                revoke_session(db, session_id, user_id)
        except:
            pass  # Token invalid, just clear cookies

    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth")

    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_tokens(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    Also rotates refresh token for security.
    """
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    user_id, session_id, token_version, user_type, company_id = validate_refresh_token(db, refresh_token)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    new_session_id, _ = rotate_refresh_token(
        db=db,
        old_session_id=session_id,
        user_id=user_id,
        token_version=token_version,
        ip_address=ip_address,
        user_agent=user_agent
    )

    new_access_token = create_access_token(
        user_id=user_id,
        company_id=company_id,
        user_type=user_type,
        token_version=token_version
    )

    new_refresh_token = create_refresh_token(
        user_id=user_id,
        session_id=new_session_id,
        token_version=token_version
    )

    db.commit()

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth"
    )

    return {"success": True, "message": "Tokens refreshed"}


@router.get("/me")
async def get_current_user_info(request: Request):
    """
    Get current user info from access token.
    Used for auth check on page load.
    """
    current_user = get_current_user_from_request(request)
    return {
        "user_id": current_user["user_id"],
        "company_id": current_user["company_id"],
        "type": current_user["type"]
    }


@router.get("/sessions")
async def get_sessions(request: Request, db: Session = Depends(get_db)):
    """
    Get all active sessions for current user.
    """
    current_user = get_current_user_from_request(request)

    if current_user["type"] == "super_admin":
        return {"sessions": []}

    sessions = get_user_sessions(db, current_user["user_id"])
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_single_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Revoke a specific session (logout from specific device).
    """
    current_user = get_current_user_from_request(request)

    if current_user["type"] == "super_admin":
        raise HTTPException(status_code=400, detail="Super admins don't have sessions")

    success = revoke_session(db, session_id, current_user["user_id"])

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"success": True, "message": "Session revoked"}


@router.post("/logout-all")
async def logout_all_devices(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Logout from all devices. Revokes all sessions and increments token version.
    """
    current_user = get_current_user_from_request(request)
    user_id = current_user["user_id"]
    is_super_admin = current_user["type"] == "super_admin"

    if not is_super_admin:
        revoke_all_sessions(db, user_id)

    increment_token_version(db, user_id, is_super_admin)

    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/auth")

    return {"success": True, "message": "Logged out from all devices"}

# ========== AGENT LOGIN ENDPOINT ==========

class AgentLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/agent-login")
async def agent_login(
    request: AgentLoginRequest,
    db: Session = Depends(get_db)
):
    """Agent login endpoint - authenticate and return agent config"""
    email = request.email
    password = request.password
    
    user = db.query(User).filter(User.email == email).first()
    
    if user and pwd_context.verify(password, user.password_hash):
        agent_token = f"agent_{secrets.token_urlsafe(32)}"
        
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "token": agent_token,
            "company_id": user.company_id,
            "user_id": user.id,
            "api_url": os.getenv("API_URL", "http://localhost:8001")
        }
    
    raise HTTPException(status_code=401, detail="Invalid email or password")


# ========== SIGNUP ENDPOINT ==========

class SignupRequest(BaseModel):
    company_name: str
    email: str
    password: str
    full_name: str
    product_type: str = "form_testing"
    plan: Optional[str] = None  # 'byok_instant' if chosen on marketing site
    claude_api_key: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: str

@router.post("/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Create new company, admin user, and subscription. Sends verification email."""
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    product = db.query(Product).filter(Product.type == request.product_type).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product type")

    # Determine if BYOK instant signup
    is_byok_instant = request.plan == "byok_instant" and request.claude_api_key

    if request.plan == "byok_instant" and not request.claude_api_key:
        raise HTTPException(status_code=400, detail="API key required for BYOK plan")

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    verification_token_hash = hashlib.sha256(verification_token.encode()).hexdigest()
    verification_expires_at = datetime.utcnow() + timedelta(hours=24)

    try:
        company = Company(
            name=request.company_name,
            billing_email=request.email,
            access_model='byok' if is_byok_instant else None,
            access_status='active' if is_byok_instant else 'pending',
            onboarding_completed=False
        )
        db.add(company)
        db.flush()
        
        user = User(
            company_id=company.id,
            email=request.email,
            password_hash=pwd_context.hash(request.password),
            name=request.full_name,
            role="admin",
            totp_enabled=False,
            totp_secret=None,
            is_verified=False,
            email_verification_token_hash=verification_token_hash,
            email_verification_expires_at=verification_expires_at,
            email_verification_sent_at=datetime.utcnow()
        )
        db.add(user)
        db.flush()

        subscription = CompanyProductSubscription(
            company_id=company.id,
            product_id=product.id,
            status="pending",
            is_trial=True,
            customer_claude_api_key=request.claude_api_key if is_byok_instant else None
        )
        db.add(subscription)
        
        project = Project(
            company_id=company.id,
            product_id=product.id,
            name="My First Project",
            description="Default project created during signup",
            created_by_user_id=user.id
        )
        db.add(project)

        # Record rate limit entry
        rate_limit_entry = EmailVerificationRateLimit(
            email=request.email,
            sent_at=datetime.utcnow()
        )
        db.add(rate_limit_entry)
        
        db.commit()

        # Send verification email
        from services.email_service import send_verification_email_queued
        email_result = send_verification_email_queued(
            to_email=request.email,
            to_name=request.full_name,
            verification_token=verification_token
        )

        if not email_result.get("success"):
            # Log error but don't fail signup - user can resend
            print(f"Failed to send verification email: {email_result.get('error')}")

        return {
            "status": "verification_required",
            "message": "Please check your email to verify your account"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email address using token. Returns status only, no session token."""
    if not request.token:
        return {"status": "invalid"}

    # Hash the incoming token
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()

    # Find user with this token hash
    user = db.query(User).filter(User.email_verification_token_hash == token_hash).first()

    if not user:
        return {"status": "invalid"}

    # Check if already verified
    if user.is_verified:
        return {"status": "already_verified"}

    # Check if token expired
    if user.email_verification_expires_at and datetime.utcnow() > user.email_verification_expires_at:
        return {"status": "expired"}

    # Verify the user
    user.is_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()

    return {"status": "email_verified"}


@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification email. Always returns 200 to prevent email enumeration."""
    email = request.email.lower().strip()

    # Check rate limits (1/min, 5/hour per email)
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    recent_minute = db.query(func.count(EmailVerificationRateLimit.id)).filter(
        EmailVerificationRateLimit.email == email,
        EmailVerificationRateLimit.sent_at > one_minute_ago
    ).scalar()

    if recent_minute >= 1:
        # Rate limited but still return success to prevent enumeration
        return {"status": "sent"}

    recent_hour = db.query(func.count(EmailVerificationRateLimit.id)).filter(
        EmailVerificationRateLimit.email == email,
        EmailVerificationRateLimit.sent_at > one_hour_ago
    ).scalar()

    if recent_hour >= 5:
        # Rate limited but still return success to prevent enumeration
        return {"status": "sent"}

    # Find user
    user = db.query(User).filter(User.email == email).first()

    # If user doesn't exist or is already verified, still return success (no enumeration)
    if not user or user.is_verified:
        return {"status": "sent"}

    # Generate new verification token (invalidates old one)
    verification_token = secrets.token_urlsafe(32)
    verification_token_hash = hashlib.sha256(verification_token.encode()).hexdigest()

    user.email_verification_token_hash = verification_token_hash
    user.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
    user.email_verification_sent_at = datetime.utcnow()

    # Record rate limit entry
    rate_limit_entry = EmailVerificationRateLimit(
        email=email,
        sent_at=datetime.utcnow()
    )
    db.add(rate_limit_entry)

    db.commit()

    # Send verification email
    from services.email_service import send_verification_email_queued
    send_verification_email_queued(
        to_email=user.email,
        to_name=user.name,
        verification_token=verification_token
    )

    return {"status": "sent"}


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset. Always returns success to prevent email enumeration.
    """
    email = request.email.lower().strip()

    # Check rate limits (1/min, 5/hour per email)
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    recent_minute = db.query(func.count(EmailVerificationRateLimit.id)).filter(
        EmailVerificationRateLimit.email == email,
        EmailVerificationRateLimit.sent_at > one_minute_ago
    ).scalar()

    if recent_minute >= 1:
        return {"status": "sent"}

    recent_hour = db.query(func.count(EmailVerificationRateLimit.id)).filter(
        EmailVerificationRateLimit.email == email,
        EmailVerificationRateLimit.sent_at > one_hour_ago
    ).scalar()

    if recent_hour >= 5:
        return {"status": "sent"}

    # Check regular user first
    user = db.query(User).filter(User.email == email).first()

    # Check super admin if no regular user found
    super_admin = None
    if not user:
        super_admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()

    # If neither exists, still return success (no enumeration)
    if not user and not super_admin:
        return {"status": "sent"}

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
    reset_expires_at = datetime.utcnow() + timedelta(hours=1)

    # Store token based on user type
    if user:
        user.password_reset_token_hash = reset_token_hash
        user.password_reset_expires_at = reset_expires_at
    else:
        super_admin.password_reset_token_hash = reset_token_hash
        super_admin.password_reset_expires_at = reset_expires_at

    # Record rate limit entry
    rate_limit_entry = EmailVerificationRateLimit(
        email=email,
        sent_at=datetime.utcnow()
    )
    db.add(rate_limit_entry)
    db.commit()

    # Send reset email
    from services.email_service import send_password_reset_email_queued
    target_name = user.name if user else super_admin.name
    send_password_reset_email_queued(
        to_email=email,
        to_name=target_name or "User",
        reset_token=reset_token
    )

    return {"status": "sent"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using token from email.
    """
    if not request.token or not request.new_password:
        raise HTTPException(status_code=400, detail="Token and new password required")

    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Hash the incoming token
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()

    # Check regular users first
    user = db.query(User).filter(User.password_reset_token_hash == token_hash).first()

    if user:
        # Check expiration
        if user.password_reset_expires_at and datetime.utcnow() > user.password_reset_expires_at:
            raise HTTPException(status_code=400, detail="Reset link has expired")

        # Update password
        user.password_hash = pwd_context.hash(request.new_password)
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        db.commit()

        return {"status": "success", "message": "Password updated successfully"}

    # Check super admins
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.password_reset_token_hash == token_hash).first()

    if super_admin:
        # Check expiration
        if super_admin.password_reset_expires_at and datetime.utcnow() > super_admin.password_reset_expires_at:
            raise HTTPException(status_code=400, detail="Reset link has expired")

        # Update password
        super_admin.password_hash = pwd_context.hash(request.new_password)
        super_admin.password_reset_token_hash = None
        super_admin.password_reset_expires_at = None
        db.commit()

        return {"status": "success", "message": "Password updated successfully"}

    raise HTTPException(status_code=400, detail="Invalid or expired reset link")