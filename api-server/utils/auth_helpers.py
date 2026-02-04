from fastapi import HTTPException, Header, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from models.database import User, SuperAdmin, UserSession, LoginAttempt
from datetime import datetime, timedelta
import os
import secrets
import hashlib

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Rate limiting settings
MAX_LOGIN_ATTEMPTS_PER_EMAIL = 5
MAX_LOGIN_ATTEMPTS_PER_IP = 20
RATE_LIMIT_WINDOW_MINUTES = 15


def get_token_from_header(authorization: str) -> str:
    """Extract token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.replace("Bearer ", "")


def decode_token(token: str) -> dict:
    """Decode JWT token and return payload."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(authorization: str, db: Session) -> User:
    """Get user from Authorization header."""
    token = get_token_from_header(authorization)
    payload = decode_token(token)

    if payload.get("type") == "super_admin":
        raise HTTPException(status_code=403, detail="Use super admin endpoints")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_super_admin(authorization: str, db: Session) -> SuperAdmin:
    """Get super admin from Authorization header."""
    token = get_token_from_header(authorization)
    payload = decode_token(token)

    if payload.get("type") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")

    admin = db.query(SuperAdmin).filter(SuperAdmin.id == payload.get("user_id")).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Super admin not found")
    return admin


def verify_company_access(authorization: str, company_id: int, db: Session = None) -> dict:
    """
    Verify token's company_id matches request.
    100% scalable - no DB query, JWT decode only.

    Args:
        authorization: Bearer token header
        company_id: Company ID from request
        db: Not used (kept for backward compatibility)

    Returns:
        Token payload dict with user_id, company_id, type
    """
    token = get_token_from_header(authorization)
    payload = decode_token(token)

    if payload.get("type") == "super_admin":
        # Super admin can access any company
        return payload

    token_company_id = payload.get("company_id")
    if token_company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return payload


def get_current_user_from_request(request: Request) -> dict:
    """
    Extract user from cookie (frontend) or header (agent).
    100% scalable - JWT decode only, no DB query.

    Returns: {"user_id": int, "company_id": int, "type": str}
    """
    token = None

    # Try cookie first (frontend)
    token = request.cookies.get("access_token")

    # Fallback to Authorization header (agent)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)

    return {
        "user_id": payload.get("user_id"),
        "company_id": payload.get("company_id"),
        "type": payload.get("type")
    }


def create_access_token(user_id: int, company_id: int, user_type: str, token_version: int) -> str:
    """
    Create short-lived access token (15 min).
    100% scalable - contains all needed info, no DB lookup required.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "company_id": company_id,
        "type": user_type,
        "token_version": token_version,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int, session_id: int, token_version: int) -> str:
    """
    Create long-lived refresh token (30 days).
    Contains session_id for DB lookup on refresh.
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "token_version": token_version,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
        db: Session,
        user_id: int,
        token_version: int,
        ip_address: str = None,
        user_agent: str = None
) -> tuple:
    """
    Create a new session and return (access_token, refresh_token).
    Stores refresh token hash in DB.
    """
    # Generate a random refresh token base
    refresh_token_raw = secrets.token_urlsafe(32)
    refresh_token_hash = hash_token(refresh_token_raw)

    # Extract device info from user agent
    device_info = None
    if user_agent:
        device_info = user_agent[:255]  # Truncate if too long

    # Create session in DB
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    session = UserSession(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        device_info=device_info,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session)
    db.flush()  # Get the session ID

    # Create tokens
    # Note: We need company_id and type, so caller must provide user object
    # This function returns session_id, caller creates tokens

    return session.id, refresh_token_raw


def create_tokens_for_user(
        db: Session,
        user: User,
        ip_address: str = None,
        user_agent: str = None
) -> tuple:
    """
    Create access and refresh tokens for a user.
    Returns (access_token, refresh_token, session_id).
    """
    user_type = user.role if user.role else "user"
    token_version = user.token_version or 1

    # Create session and get refresh token
    session_id, refresh_token_raw = create_session(
        db=db,
        user_id=user.id,
        token_version=token_version,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        company_id=user.company_id,
        user_type=user_type,
        token_version=token_version
    )

    # Create refresh token (JWT containing session_id)
    refresh_token = create_refresh_token(
        user_id=user.id,
        session_id=session_id,
        token_version=token_version
    )

    db.commit()

    return access_token, refresh_token, session_id


def create_tokens_for_super_admin(admin: SuperAdmin) -> str:
    """
    Create access token for super admin (NO refresh token).
    Super admins must re-authenticate after 1 hour for security.
    Returns access_token only.
    """
    token_version = admin.token_version or 1

    # Create access token (1 hour for super admin - shorter for security)
    expire = datetime.utcnow() + timedelta(hours=1)
    access_payload = {
        "user_id": admin.id,
        "company_id": None,
        "type": "super_admin",
        "token_version": token_version,
        "exp": expire
    }
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")

    return access_token


def validate_refresh_token(db: Session, refresh_token: str) -> tuple:
    """
    Validate refresh token and return user/session info.
    Returns (user_id, session_id, token_version, user_type, company_id) or raises HTTPException.

    This DOES query DB (by design - refresh happens every 15 min, not every request).
    """
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    session_id = payload.get("session_id")
    user_id = payload.get("user_id")
    token_version_from_token = payload.get("token_version")

    # Lookup session in DB
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user_id
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Session not found")

    if session.is_revoked:
        raise HTTPException(status_code=401, detail="Session has been revoked")

    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")

    # Get user to check token_version
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Super admins don't use refresh tokens
        raise HTTPException(status_code=401, detail="User not found")

    # Check token version
    if user.token_version != token_version_from_token:
        raise HTTPException(status_code=401, detail="Token has been invalidated")

    # Update session last_used_at
    session.last_used_at = datetime.utcnow()
    db.commit()

    user_type = user.role if user.role else "user"
    return user_id, session_id, user.token_version, user_type, user.company_id


def rotate_refresh_token(
        db: Session,
        old_session_id: int,
        user_id: int,
        token_version: int,
        ip_address: str = None,
        user_agent: str = None
) -> tuple:
    """
    Rotate refresh token - invalidate old session, create new one.
    Returns (new_session_id, new_refresh_token_raw).
    """
    # Revoke old session
    old_session = db.query(UserSession).filter(UserSession.id == old_session_id).first()
    if old_session:
        old_session.is_revoked = True

    # Create new session
    return create_session(
        db=db,
        user_id=user_id,
        token_version=token_version,
        ip_address=ip_address,
        user_agent=user_agent
    )


def check_rate_limit(db: Session, email: str, ip_address: str = None) -> bool:
    """
    Check if login is rate limited.
    Returns True if allowed, raises HTTPException if rate limited.
    """
    window_start = datetime.utcnow() - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)

    # Check email-based rate limit
    email_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.email == email.lower(),
        LoginAttempt.attempted_at > window_start,
        LoginAttempt.success == False
    ).count()

    if email_attempts >= MAX_LOGIN_ATTEMPTS_PER_EMAIL:
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please try again in {RATE_LIMIT_WINDOW_MINUTES} minutes."
        )

    # Check IP-based rate limit
    if ip_address:
        ip_attempts = db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.attempted_at > window_start,
            LoginAttempt.success == False
        ).count()

        if ip_attempts >= MAX_LOGIN_ATTEMPTS_PER_IP:
            raise HTTPException(
                status_code=429,
                detail=f"Too many login attempts from this IP. Please try again in {RATE_LIMIT_WINDOW_MINUTES} minutes."
            )

    return True


def log_login_attempt(db: Session, email: str, ip_address: str = None, success: bool = False):
    """Log a login attempt for rate limiting and audit."""
    attempt = LoginAttempt(
        email=email.lower(),
        ip_address=ip_address,
        success=success
    )
    db.add(attempt)
    db.commit()


def revoke_session(db: Session, session_id: int, user_id: int):
    """Revoke a specific session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user_id
    ).first()

    if session:
        session.is_revoked = True
        db.commit()
        return True
    return False


def revoke_all_sessions(db: Session, user_id: int):
    """Revoke all sessions for a user."""
    db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()


def increment_token_version(db: Session, user_id: int, is_super_admin: bool = False):
    """
    Increment token version to invalidate all existing tokens.
    Used for "logout all devices" feature.
    """
    if is_super_admin:
        admin = db.query(SuperAdmin).filter(SuperAdmin.id == user_id).first()
        if admin:
            admin.token_version = (admin.token_version or 1) + 1
    else:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.token_version = (user.token_version or 1) + 1

    db.commit()


def get_user_sessions(db: Session, user_id: int) -> list:
    """Get all active sessions for a user."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False,
        UserSession.expires_at > datetime.utcnow()
    ).order_by(UserSession.last_used_at.desc()).all()

    return [
        {
            "id": s.id,
            "device_info": s.device_info,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None
        }
        for s in sessions
    ]

def verify_user_access(authorization: str, user_id: int, db: Session) -> User:
    """Verify token matches user_id. Returns user if valid."""
    user = get_current_user(authorization, db)
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


def log_super_admin_action(
        db: Session,
        admin_id: int,
        action: str,
        target_company_id: int = None,
        details: dict = None,
        ip_address: str = None
):
    """Log super admin action for audit trail."""
    from models.database import SuperAdminAuditLog
    log_entry = SuperAdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_company_id=target_company_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log_entry)
    db.commit()