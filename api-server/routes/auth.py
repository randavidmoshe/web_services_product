from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, SuperAdmin, User
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import os
import secrets
from pydantic import BaseModel

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
        return {"token": create_token({"user_id": admin.id, "type": "super_admin"}), "type": "super_admin"}
    
    # Check regular user
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):
        user.last_login_at = datetime.utcnow()
        db.commit()
        return {"token": create_token({"user_id": user.id, "type": "user"}), "type": "user"}
    
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
