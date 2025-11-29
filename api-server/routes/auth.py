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
        return {
            "token": create_token({"user_id": admin.id, "type": "super_admin"}),
            "type": "super_admin",
            "user_id": admin.id,
            "company_id": None  # Super admins don't belong to a company
        }
    
    # Check regular user
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        # Use actual user role from database (admin, user, etc.)
        user_type = user.role if user.role else "user"
        
        return {
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
    
    # Check regular user (agents use regular user accounts)
    user = db.query(User).filter(User.email == email).first()
    
    if user and pwd_context.verify(password, user.password_hash):
        # Generate agent token
        agent_token = f"agent_{secrets.token_urlsafe(32)}"
        
        # Update last login
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
    product_type: str = "form_testing"  # form_testing, shopping_testing, marketing_testing
    plan: str = "trial"  # trial, trial_byok, starter, professional
    claude_api_key: Optional[str] = None  # Only for trial_byok


@router.post("/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create new company, admin user, and subscription.
    Plans:
    - trial: Free 14 days, $50 AI budget (hidden from user)
    - trial_byok: Free 14 days, user's own API key (unlimited)
    - starter: $300/mo, $300 AI budget
    - professional: $500/mo, $500 AI budget
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get product
    product = db.query(Product).filter(Product.type == request.product_type).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product type")
    
    # Plan configuration
    plan_config = {
        "trial": {"cost": 0, "budget": 50, "is_trial": True, "days": 14},
        "trial_byok": {"cost": 0, "budget": 0, "is_trial": True, "days": 14},
        "starter": {"cost": 300, "budget": 300, "is_trial": False, "days": None},
        "professional": {"cost": 500, "budget": 500, "is_trial": False, "days": None},
    }
    
    if request.plan not in plan_config:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    config = plan_config[request.plan]
    
    # BYOK requires API key
    if request.plan == "trial_byok" and not request.claude_api_key:
        raise HTTPException(status_code=400, detail="API key required for BYOK plan")
    
    try:
        # 1. Create company
        company = Company(
            name=request.company_name,
            billing_email=request.email
        )
        db.add(company)
        db.flush()  # Get company.id
        
        # 2. Create admin user
        user = User(
            company_id=company.id,
            email=request.email,
            password_hash=pwd_context.hash(request.password),
            name=request.full_name,
            role="admin"
        )
        db.add(user)
        db.flush()  # Get user.id
        
        # 3. Create subscription
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
        
        # 4. Create default project
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
            "user_id": user.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")
