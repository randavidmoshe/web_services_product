from fastapi import HTTPException, Header
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from models.database import User, SuperAdmin
from datetime import datetime
import os

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")


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


def verify_company_access(authorization: str, company_id: int, db: Session) -> User:
    """Verify user belongs to company_id. Returns user if valid."""
    user = get_current_user(authorization, db)
    if user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


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