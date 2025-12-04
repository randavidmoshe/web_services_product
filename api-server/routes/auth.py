from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, SuperAdmin, User, Company, Product, CompanyProductSubscription, Project
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import os
import secrets
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    email = request.email
    password = request.password
    
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
        
        return {
            "requires_2fa": False,
            "token": create_token({"user_id": admin.id, "type": "super_admin"}),
            "type": "super_admin",
            "user_id": admin.id,
            "company_id": None
        }
    
    # Check regular user
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):
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
        
        if not requires_2fa_setup and user.company_id:
            company = db.query(Company).filter(Company.id == user.company_id).first()
            if company and getattr(company, 'require_2fa', False) and not getattr(user, 'totp_enabled', False):
                requires_2fa_setup = True
        
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return {
            "requires_2fa": False,
            "requires_2fa_setup": requires_2fa_setup,
            "token": create_token({"user_id": user.id, "type": user_type}),
            "type": user_type,
            "user_id": user.id,
            "company_id": user.company_id
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


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
    plan: str = "trial"
    claude_api_key: Optional[str] = None


@router.post("/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Create new company, admin user, and subscription."""
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    product = db.query(Product).filter(Product.type == request.product_type).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product type")
    
    plan_config = {
        "trial": {"cost": 0, "budget": 50, "is_trial": True, "days": 14},
        "trial_byok": {"cost": 0, "budget": 0, "is_trial": True, "days": 14},
        "starter": {"cost": 300, "budget": 300, "is_trial": False, "days": None},
        "professional": {"cost": 500, "budget": 500, "is_trial": False, "days": None},
    }
    
    if request.plan not in plan_config:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    config = plan_config[request.plan]
    
    if request.plan == "trial_byok" and not request.claude_api_key:
        raise HTTPException(status_code=400, detail="API key required for BYOK plan")
    
    try:
        company = Company(
            name=request.company_name,
            billing_email=request.email
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
            totp_secret=None
        )
        db.add(user)
        db.flush()
        
        subscription = CompanyProductSubscription(
            company_id=company.id,
            product_id=product.id,
            status="trial" if config["is_trial"] else "active",
            is_trial=config["is_trial"],
            trial_ends_at=datetime.utcnow() + timedelta(days=config["days"]) if config["days"] else None,
            monthly_subscription_cost=config["cost"],
            monthly_claude_budget=config["budget"],
            customer_claude_api_key=request.claude_api_key if request.plan == "trial_byok" else None
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
        
        db.commit()
        
        return {
            "success": True,
            "message": "Account created successfully",
            "company_id": company.id,
            "user_id": user.id,
            "token": create_token({"user_id": user.id, "type": "admin"}),
            "type": "admin",
            "requires_2fa_setup": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")
