"""
User Management Routes
- List users (company admin sees own company, super admin sees all)
- Create users (admin creates users for their company)
- Update users
- Delete users
- Reset 2FA
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from models.database import get_db, User, SuperAdmin, Company
from passlib.context import CryptContext
from jose import jwt, JWTError
import os
import secrets

router = APIRouter(prefix="/api/users", tags=["Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")


# ========== Request/Response Models ==========

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"  # "user" or "admin"

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

    class Config:
        from_attributes = True


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
        # Super admin can see all users
        query = db.query(User)
        if company_id:
            query = query.filter(User.company_id == company_id)
        users = query.all()
    elif user_type == "admin":
        # Company admin sees only their company's users
        users = db.query(User).filter(User.company_id == user.company_id).all()
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Build response with company names
    result = []
    for u in users:
        company = db.query(Company).filter(Company.id == u.company_id).first()
        result.append(UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role or "user",
            company_id=u.company_id,
            company_name=company.name if company else None,
            totp_enabled=getattr(u, 'totp_enabled', False),
            created_at=u.created_at,
            last_login_at=u.last_login_at
        ))
    
    return result


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Create a new user in the admin's company.
    - Super admin: cannot create users this way (companies manage their own users)
    - Company admin: creates users for their company
    - Regular user: no access
    """
    current_user, user_type = get_current_user_and_type(authorization, db)
    
    if user_type == "super_admin":
        raise HTTPException(status_code=400, detail="Super admin cannot create company users. Use company admin account.")
    
    if user_type != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    if user_data.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
    
    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=pwd_context.hash(user_data.password),
        name=user_data.name,
        role=user_data.role,
        company_id=current_user.company_id,
        created_by_admin_id=current_user.id,
        agent_api_token=f"agent_{secrets.token_urlsafe(32)}"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    company = db.query(Company).filter(Company.id == new_user.company_id).first()
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role or "user",
        company_id=new_user.company_id,
        company_name=company.name if company else None,
        totp_enabled=getattr(new_user, 'totp_enabled', False),
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at
    )


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
        pass  # Can update anyone
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
        # Check if new email is taken
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        target_user.email = user_data.email
    
    db.commit()
    db.refresh(target_user)
    
    company = db.query(Company).filter(Company.id == target_user.company_id).first()
    
    return UserResponse(
        id=target_user.id,
        email=target_user.email,
        name=target_user.name,
        role=target_user.role or "user",
        company_id=target_user.company_id,
        company_name=company.name if company else None,
        totp_enabled=getattr(target_user, 'totp_enabled', False),
        created_at=target_user.created_at,
        last_login_at=target_user.last_login_at
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
        pass  # Can delete anyone
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
        pass  # Can reset anyone
    elif user_type == "admin":
        if target_user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot reset 2FA for users from other companies")
        if target_user.role == "admin" and target_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Cannot reset 2FA for other admins. Contact super admin.")
    else:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    
    # Reset 2FA
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
