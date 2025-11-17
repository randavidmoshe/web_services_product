from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from models.database import get_db, User
import secrets

router = APIRouter()

@router.post("/generate-token")
async def generate_agent_token(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    if not user.agent_api_token:
        user.agent_api_token = secrets.token_urlsafe(32)
        db.commit()
    
    return {"token": user.agent_api_token}

@router.post("/validate")
async def validate_token(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.agent_api_token == token).first()
    if not user:
        raise HTTPException(401, "Invalid token")
    
    return {
        "user_id": user.id,
        "company_id": user.company_id,
        "email": user.email
    }

@router.get("/commands")
async def get_commands(authorization: str = Header(None), db: Session = Depends(get_db)):
    # Parse token from "Bearer TOKEN"
    token = authorization.replace("Bearer ", "") if authorization else None
    user = db.query(User).filter(User.agent_api_token == token).first()
    if not user:
        raise HTTPException(401, "Invalid token")
    
    # TODO: Return pending commands for this user
    return []
