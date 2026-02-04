from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from models.database import get_db, User
from models.agent_models import Agent
from datetime import datetime, timedelta
import secrets
from utils.auth_helpers import get_current_user_from_request

router = APIRouter()

# Heartbeat timeout - agent is offline if no heartbeat for this long
HEARTBEAT_TIMEOUT_SECONDS = 60


@router.get("/status")
async def get_agent_status(user_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Get agent status for a specific user.
    Scalable endpoint - returns only ONE agent's status.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    agent = db.query(Agent).filter(Agent.user_id == user_id).first()

    if not agent:
        return {
            "status": "not_registered",
            "last_heartbeat": None
        }

    if current_user["type"] != "super_admin" and agent.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if agent is online (heartbeat within timeout)
    is_online = False
    if agent.last_heartbeat:
        timeout_threshold = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
        is_online = agent.last_heartbeat > timeout_threshold
    
    return {
        "status": "online" if is_online else "offline",
        "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None
    }

@router.post("/generate-token")
async def generate_agent_token(user_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if current_user["type"] != "super_admin" and user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
