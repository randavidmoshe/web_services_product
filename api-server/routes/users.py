"""
User Management Routes with Email Invitation System
- List users (company admin sees own company, super admin sees all)
- Invite users (sends email invitation)
- Accept invitation (user sets password)
- Update users
- Delete users
- Reset 2FA
- Resend invitation
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from models.database import get_db, User, SuperAdmin, Company
from services.email_service import send_invitation_email
from passlib.context import CryptContext
from jose import jwt, JWTError
import os
import secrets

router = APIRouter(prefix="/api/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

# Invitation token expiry (7 days)
INVITE_TOKEN_EXPIRY_DAYS = 7


# ========== Request/Response Models ==========

class UserInvite(BaseModel):
    """Request model for inviting a new user"""
    email: str
    name: str
    role: str = "user"  # "user" or "admin"

class AcceptInvite(BaseModel):
    """Request model for accepting an invitation"""
    token: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    company_id: int
    company_name: Optional[str] = None
    totp_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    invite_pending: bool = False

    class Config:
        from_attributes = True

class InviteInfoResponse(BaseModel):
    """Response for invitation info lookup"""
    valid: bool
    email: Optional[str] = None
    name: Optional[str] = None
    company_name: Optional[str] = None
    expired: bool = False
    already_accepted: bool = False


# ========== Helper Functions ==========

def get_current_user_and_type(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Extract and validate user from JWT token, return user and type"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
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


def generate_invite_token() -> str:
    """Generate a secure random invitation token"""
    return secrets.token_urlsafe(48)


def is_invite_expired(invite_sent_at: datetime) -> bool:
    """Check if an invitation has expired"""
    if not invite_sent_at:
        return True
    expiry_time = invite_sent_at + timedelta(days=INVITE_TOKEN_EXPIRY_DAYS)
    return datetime.utcnow() > expiry_time


# ========== Endpoints ==========

@router.get("", response_model=List[UserResponse])
async def list_users(
    company_id: Optional[int] = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    List users.
    - Super admin: sees all users (can filter by company_id)
    - Company admin: sees only users in their company
    - Regular user: no access
    """
    user, user_type = get_current_user_and_type(authorization, db)
    
    if user_type == "super_admin":
        query = db.query(User)
        if company_id:
            query = query.filter(User.company_id == company_id)
        users = query.all()
    elif user_type == "admin":
        users = db.query(User).filter(User.company_id == user.company_id).all()
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    result = []
    for u in users:
        company = db.query(Company).filter(Company.id == u.company_id).first()
        
        # Check if user has pending invitation (no password set)
        invite_pending = not u.password_hash or u.password_hash == ""
        
        result.append(UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role or "user",
            company_id=u.company_id,
            company_name=company.name if company else None,
            totp_enabled=getattr(u, 'totp_enabled', False),
            created_at=u.created_at,
            last_login_at=u.last_login_at,
            invite_pending=invite_pending
        ))
    
    return result


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    user_data: UserInvite,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Invite a new user to the company.
    Sends an email invitation with a link to set up their account.
    
    - Super admin: cannot invite users this way
    - Company admin: invites users to their company
    - Regular user: no access
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    if user_type == "super_admin":
        raise HTTPException(status_code=400, detail="Super admin cannot invite company users. Use company admin account.")
    
    if user_type != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    if user_data.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
    
    # Get company info
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=400, detail="Company not found")
    
    # Generate invitation token
    invite_token = generate_invite_token()
    
    # Create user with pending status (no password)
    new_user = User(
        email=user_data.email,
        password_hash="",  # Empty - will be set when invitation is accepted
        name=user_data.name,
        role=user_data.role,
        company_id=current_user.company_id,
        created_by_admin_id=current_user.id,
        agent_api_token=f"agent_{secrets.token_urlsafe(32)}",
        invite_token=invite_token,
        invite_sent_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send invitation email
    email_result = send_invitation_email(
        to_email=user_data.email,
        to_name=user_data.name,
        inviter_name=current_user.name,
        company_name=company.name,
        invite_token=invite_token
    )
    
    if not email_result.get("success"):
        # Log the error but don't fail - user can be resent invitation
        print(f"Warning: Failed to send invitation email: {email_result.get('error')}")
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role or "user",
        company_id=new_user.company_id,
        company_name=company.name,
        totp_enabled=False,
        created_at=new_user.created_at,
        last_login_at=None,
        invite_pending=True
    )


@router.get("/invite/{token}", response_model=InviteInfoResponse)
async def get_invite_info(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Get information about an invitation.
    Used by the accept-invite page to show user info.
    No authentication required.
    """
    user = db.query(User).filter(User.invite_token == token).first()
    
    if not user:
        return InviteInfoResponse(valid=False)
    
    # Check if already accepted (has password)
    if user.password_hash and user.password_hash != "":
        return InviteInfoResponse(
            valid=False,
            already_accepted=True,
            email=user.email,
            name=user.name
        )
    
    # Check if expired
    if is_invite_expired(user.invite_sent_at):
        return InviteInfoResponse(
            valid=False,
            expired=True,
            email=user.email,
            name=user.name
        )
    
    # Get company name
    company = db.query(Company).filter(Company.id == user.company_id).first()
    
    return InviteInfoResponse(
        valid=True,
        email=user.email,
        name=user.name,
        company_name=company.name if company else None
    )


@router.post("/invite/accept")
async def accept_invite(
    data: AcceptInvite,
    db: Session = Depends(get_db)
):
    """
    Accept an invitation and set password.
    No authentication required - uses invite token.
    """
    user = db.query(User).filter(User.invite_token == data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid invitation token")
    
    # Check if already accepted
    if user.password_hash and user.password_hash != "":
        raise HTTPException(status_code=400, detail="Invitation already accepted. Please log in.")
    
    # Check if expired
    if is_invite_expired(user.invite_sent_at):
        raise HTTPException(status_code=400, detail="Invitation has expired. Please ask your admin to resend.")
    
    # Validate password
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Set password and clear invite token
    user.password_hash = pwd_context.hash(data.password)
    user.invite_token = None
    user.invite_accepted_at = datetime.utcnow()
    
    db.commit()
    
    # Get company for response
    company = db.query(Company).filter(Company.id == user.company_id).first()
    
    return {
        "success": True,
        "message": "Account created successfully! You can now log in.",
        "email": user.email,
        "company_name": company.name if company else None
    }


@router.post("/{user_id}/resend-invite")
async def resend_invite(
    user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Resend invitation email to a user who hasn't accepted yet.
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Permission check
    if user_type == "super_admin":
        pass
    elif user_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot resend invite for users from other companies")
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if invitation is still pending
    if target_user.password_hash and target_user.password_hash != "":
        raise HTTPException(status_code=400, detail="User has already accepted the invitation")
    
    # Generate new token
    new_token = generate_invite_token()
    target_user.invite_token = new_token
    target_user.invite_sent_at = datetime.utcnow()
    
    db.commit()
    
    # Get company and inviter info
    company = db.query(Company).filter(Company.id == target_user.company_id).first()
    inviter_name = current_user.name if hasattr(current_user, 'name') else "Admin"
    
    # Send email
    email_result = send_invitation_email(
        to_email=target_user.email,
        to_name=target_user.name,
        inviter_name=inviter_name,
        company_name=company.name if company else "Your Company",
        invite_token=new_token
    )
    
    if not email_result.get("success"):
        raise HTTPException(status_code=500, detail=f"Failed to send email: {email_result.get('error')}")
    
    return {"success": True, "message": f"Invitation resent to {target_user.email}"}


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Update a user.
    - Super admin: can update any user
    - Company admin: can update users in their company
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Permission check
    if user_type == "super_admin":
        pass
    elif user_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot update users from other companies")
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Update fields
    if user_data.name is not None:
        target_user.name = user_data.name
    if user_data.role is not None:
        if user_data.role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
        target_user.role = user_data.role
    if user_data.email is not None:
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        target_user.email = user_data.email
    
    db.commit()
    db.refresh(target_user)
    
    company = db.query(Company).filter(Company.id == target_user.company_id).first()
    invite_pending = not target_user.password_hash or target_user.password_hash == ""
    
    return UserResponse(
        id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role=target_user.role or "user",
        company_id=target_user.company_id,
        company_name=company.name if company else None,
        totp_enabled=getattr(target_user, 'totp_enabled', False),
        created_at=target_user.created_at,
        last_login_at=target_user.last_login_at,
        invite_pending=invite_pending
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Delete a user.
    - Super admin: can delete any user
    - Company admin: can delete users in their company (not themselves, not other admins)
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Permission check
    if user_type == "super_admin":
        pass
    elif user_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot delete users from other companies")
        if target_user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        if target_user.role == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete other admins. Contact super admin.")
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    db.delete(target_user)
    db.commit()
    
    return {"success": True, "message": "User deleted"}


@router.post("/{user_id}/reset-2fa")
async def reset_user_2fa(
    user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Reset a user's 2FA (disable it so they can set up again).
    - Super admin: can reset anyone's 2FA
    - Company admin: can reset users in their company (not other admins)
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Permission check
    if user_type == "super_admin":
        pass
    elif user_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot reset 2FA for users from other companies")
        if target_user.role == "admin" and target_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Cannot reset 2FA for other admins. Contact super admin.")
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    target_user.totp_secret = None
    target_user.totp_enabled = False
    db.commit()
    
    return {"success": True, "message": f"2FA reset for {target_user.email}"}


@router.get("/companies")
async def list_companies(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    List all companies. Super admin only.
    """
    user, user_type = get_current_user_and_type(authorization, db)
    
    if user_type != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    companies = db.query(Company).all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "billing_email": c.billing_email,
            "created_at": c.created_at,
            "require_2fa": getattr(c, 'require_2fa', False)
        }
        for c in companies
    ]
