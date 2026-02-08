# Agent API Router - 3-Layer Security Implementation
# Location: api-server/routes/agent_router.py
#
# Security Levels:
# - Level 1: HTTPS/SSL (handled by Nginx)
# - Level 2: API Key - permanent agent identity
# - Level 3: JWT Token - short-lived access with session enforcement
#
# Single Agent Enforcement:
# - Each user can only have ONE active agent
# - Registering a new agent generates NEW API key (invalidates previous agent)
# - JWT session_id must match DB to prevent old agents from reconnecting

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import redis
import json
import os
import uuid
import secrets

from models.database import get_db, CrawlSession
from models.agent_models import Agent, AgentTask
from services.agent_service import AgentService
from utils.jwt_utils import create_jwt_token, decode_jwt_token, get_token_expiry_seconds
from jose import JWTError
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Redis connection with explicit pool
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
_agent_router_redis_pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=20)
redis_client = redis.Redis(connection_pool=_agent_router_redis_pool)


# ============================================================================
# SECURITY UTILITIES
# ============================================================================

def generate_api_key() -> str:
    """Generate a secure random API key (43 characters)"""
    return secrets.token_urlsafe(32)


def generate_session_id() -> str:
    """Generate a unique session ID (32 characters)"""
    return secrets.token_urlsafe(24)


def validate_api_key_only(
    x_agent_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Agent:
    """
    Level 2 Only: Validate API key from X-Agent-API-Key header.
    Used for /refresh-token endpoint (doesn't need JWT).
    """
    if not x_agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-Agent-API-Key header."
        )
    
    agent = db.query(Agent).filter(Agent.api_key == x_agent_api_key).first()
    
    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Agent may have been replaced by another registration."
        )
    
    return agent


def validate_jwt_and_session(
    authorization: Optional[str] = Header(None),
    x_agent_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Agent:
    """
    Level 2+3: Full validation - API key AND JWT with session check.
    
    This ensures:
    1. API key is valid
    2. JWT token is valid and not expired
    3. Session ID in JWT matches current session in DB (single agent enforcement)
    """
    # Check API key header
    if not x_agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-Agent-API-Key header."
        )
    
    # Check Authorization header
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing JWT token. Include Authorization: Bearer <token> header."
        )
    
    if not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header. Use 'Bearer <token>' format."
        )
    
    token = authorization[7:]  # Remove 'Bearer ' prefix
    
    # Decode JWT
    try:
        payload = decode_jwt_token(token)
    except JWTError as e:
        error_msg = str(e).lower()
        if 'expired' in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Token expired. Call POST /api/agent/refresh-token to get a new token."
            )
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    
    # Verify API key matches token
    if payload.get('api_key') != x_agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key mismatch. Token was issued for a different API key."
        )
    
    # Get agent from DB
    agent = db.query(Agent).filter(Agent.api_key == x_agent_api_key).first()
    
    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Agent may have been replaced by another registration."
        )
    
    # CHECK SESSION MATCHES - This kills old agents!
    if agent.current_session_id != payload.get('session_id'):
        raise HTTPException(
            status_code=401,
            detail="Session invalidated. Another agent has connected for this user. This agent is now disabled."
        )
    
    return agent


# ============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# ============================================================================

@router.post("/register")
async def register_agent(
    agent_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Register agent and receive API key + JWT token.
    
    IMPORTANT: If user already has an agent, this generates a NEW API key,
    which permanently invalidates the old agent.
    
    Returns:
    {
        "success": True,
        "api_key": "new-api-key...",
        "jwt": "eyJ...",
        "expires_in": 1800,
        "agent_id": "agent-test-001"
    }
    """
    agent_id = agent_data.get('agent_id')
    company_id = agent_data.get('company_id')
    user_id = agent_data.get('user_id')
    hostname = agent_data.get('hostname')
    platform = agent_data.get('platform')
    version = agent_data.get('version', '2.0.0')
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")
    
    # Check if user already has an agent (by user_id, not agent_id)
    existing_agent = db.query(Agent).filter(Agent.user_id == user_id).first()
    
    if existing_agent:
        # User already has an agent - REGENERATE API KEY to invalidate old agent!
        existing_agent.api_key = generate_api_key()
        existing_agent.current_session_id = generate_session_id()
        existing_agent.agent_id = agent_id
        existing_agent.company_id = company_id
        existing_agent.hostname = hostname
        existing_agent.platform = platform
        existing_agent.version = version
        existing_agent.status = "online"
        existing_agent.last_heartbeat = datetime.utcnow()
        existing_agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_agent)
        
        # Create JWT token
        jwt_token = create_jwt_token(
            api_key=existing_agent.api_key,
            user_id=user_id,
            agent_id=agent_id,
            session_id=existing_agent.current_session_id
        )
        
        return {
            "success": True,
            "agent_id": existing_agent.agent_id,
            "api_key": existing_agent.api_key,
            "jwt": jwt_token,
            "expires_in": get_token_expiry_seconds(),
            "message": "Registration successful. Previous agent has been invalidated."
        }
    else:
        # New user - create new agent with API key and session
        api_key = generate_api_key()
        session_id = generate_session_id()
        
        new_agent = Agent(
            agent_id=agent_id,
            company_id=company_id,
            user_id=user_id,
            hostname=hostname,
            platform=platform,
            version=version,
            status="online",
            api_key=api_key,
            current_session_id=session_id,
            last_heartbeat=datetime.utcnow()
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        # Create JWT token
        jwt_token = create_jwt_token(
            api_key=api_key,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id
        )
        
        return {
            "success": True,
            "agent_id": new_agent.agent_id,
            "api_key": api_key,
            "jwt": jwt_token,
            "expires_in": get_token_expiry_seconds(),
            "message": "Agent registered. Store credentials securely."
        }


@router.post("/refresh-token")
async def refresh_token(
    agent: Agent = Depends(validate_api_key_only),
    db: Session = Depends(get_db)
):
    """
    Get a new JWT token using API key (Level 2 only).
    Used when JWT expires but API key is still valid.
    
    Headers required:
    - X-Agent-API-Key: <api_key>
    
    Returns:
    {
        "jwt": "eyJ...",
        "expires_in": 1800
    }
    """
    jwt_token = create_jwt_token(
        api_key=agent.api_key,
        user_id=agent.user_id,
        agent_id=agent.agent_id,
        session_id=agent.current_session_id
    )
    
    return {
        "jwt": jwt_token,
        "expires_in": get_token_expiry_seconds()
    }


# ============================================================================
# PROTECTED ENDPOINTS (Require API Key + JWT)
# ============================================================================

@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat_data: dict,
    agent: Agent = Depends(validate_jwt_and_session),
    db: Session = Depends(get_db)
):
    """
    Receive heartbeat from authenticated agent.
    Requires X-Agent-API-Key AND Authorization: Bearer <jwt> headers.
    Returns cancel_requested if agent has a cancelled running session.
    """
    agent.status = heartbeat_data.get('status', 'idle')
    agent.current_task_id = heartbeat_data.get('current_task_id')
    agent.last_heartbeat = datetime.utcnow()
    db.commit()
    
    # Check for recently cancelled session (last 5 minutes)
    # Simple approach: no session ID tracking needed
    cancel_requested = False
    cancel_threshold = datetime.utcnow() - timedelta(minutes=5)
    cancelled_session = db.query(CrawlSession).filter(
        CrawlSession.user_id == agent.user_id,
        CrawlSession.status == 'cancelled',
        CrawlSession.completed_at >= cancel_threshold
    ).first()

    if cancelled_session:
        cancel_requested = True
        # Mark as acknowledged so we don't keep sending cancel
        cancelled_session.status = 'cancelled_ack'
        db.commit()

    # Check FormMapperSession (Form Mapper)
    #from models.database import FormMapperSession
    #ended_mapper = db.query(FormMapperSession).filter(
    #    FormMapperSession.user_id == agent.user_id,
    #    FormMapperSession.status.in_(['cancelled', 'completed', 'failed']),
    #    FormMapperSession.updated_at >= cancel_threshold
    #).first()

    #if ended_mapper:
    #    cancel_requested = True
    #    if ended_mapper.status == 'cancelled':
    #       ended_mapper.status = 'cancelled_ack'
    #    elif ended_mapper.status == 'completed':
    #       ended_mapper.status = 'completed_ack'
    #    elif ended_mapper.status == 'failed':
    #        ended_mapper.status = 'failed_ack'
    #    db.commit()

    return {"success": True, "cancel_requested": cancel_requested}


@router.get("/poll-task")
async def poll_task(
    agent_id: str,
    company_id: int,
    agent: Agent = Depends(validate_jwt_and_session),
    db: Session = Depends(get_db)
):
    """
    Agent polls for tasks from their user-specific Redis queue.
    Requires X-Agent-API-Key AND Authorization: Bearer <jwt> headers.
    """
    # Verify agent_id matches the authenticated agent
    if agent.agent_id != agent_id:
        raise HTTPException(
            status_code=403,
            detail="Agent ID mismatch. You can only poll tasks for your own agent."
        )
    
    try:
        # Pop task from user-specific Redis queue
        queue_name = f'agent:{agent.user_id}'
        task_data = redis_client.lpop(queue_name)
        
        if not task_data:
            raise HTTPException(status_code=204, detail="No tasks available")
        
        # Decode task data
        if isinstance(task_data, bytes):
            task_data = task_data.decode('utf-8')
        
        task_msg = json.loads(task_data)
        task_id = task_msg.get('task_id')

        # Return directly for forms_runner tasks (Redis-only for scale)
        if task_msg.get('task_type') and (task_msg.get('task_type').startswith('forms_runner_') or task_msg.get('task_type').startswith('form_mapper_')):
            return {
                'task_id': task_id,
                'task_type': task_msg.get('task_type'),
                'payload': task_msg.get('payload', {}),
                'session_id': task_msg.get('session_id')
            }
        
        # Get full task details from database
        agent_service = AgentService(db)
        db_task = agent_service.get_celery_task(task_id)
        
        if not db_task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in database")
        
        # Mark task as assigned to this agent
        agent_service.assign_celery_task_to_agent(task_id=task_id, agent_id=agent_id)

        return {
            "task_id": task_id,
            "task_type": db_task.task_type,
            "parameters": db_task.parameters
        }
        
    except HTTPException:
        raise
    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")


@router.post("/task-result")
async def update_task_result(
    result_data: dict,
    agent: Agent = Depends(validate_jwt_and_session),
    db: Session = Depends(get_db)
):
    """
    Agent sends task result.
    Requires X-Agent-API-Key AND Authorization: Bearer <jwt> headers.
    """
    task_id = result_data.get('task_id')
    status = result_data.get('status')
    result = result_data.get('result')
    error = result_data.get('error')
    
    agent_service = AgentService(db)
    agent_service.update_celery_task_result(task_id=task_id, status=status, result=result, error=error)
    
    return {"success": True}


@router.post("/task-status")
async def update_task_status(
    status_data: dict,
    agent: Agent = Depends(validate_jwt_and_session),
    db: Session = Depends(get_db)
):
    """
    Agent sends task status update.
    Requires X-Agent-API-Key AND Authorization: Bearer <jwt> headers.
    """
    task_id = status_data.get('task_id')
    status = status_data.get('status')
    message = status_data.get('message')
    result = status_data.get('result')
    
    agent_service = AgentService(db)
    
    if status == 'completed':
        agent_service.update_celery_task_result(task_id=task_id, status=status, result=result)
    elif status == 'failed':
        agent_service.update_celery_task_result(task_id=task_id, status=status, error=message)
    else:
        db_task = agent_service.get_celery_task(task_id)
        if db_task:
            db_task.status = status
            db.commit()
    
    return {"success": True}


@router.post("/task-progress")
async def update_task_progress(
    progress_data: dict,
    agent: Agent = Depends(validate_jwt_and_session)
):
    """
    Agent sends progress updates.
    Requires X-Agent-API-Key AND Authorization: Bearer <jwt> headers.
    """
    return {"success": True}


# ============================================================================
# ADMIN ENDPOINTS (No agent authentication - for dashboard)
# ============================================================================

@router.get("/agents")
async def list_agents(request: Request, db: Session = Depends(get_db)):
    """List all agents (for admin dashboard - no agent auth required)."""

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    #query = db.query(Agent)
    #if company_id:
    #    query = query.filter(Agent.company_id == company_id)

    query = db.query(Agent).filter(Agent.company_id == company_id)
    
    agents = query.all()
    
    return {
        "agents": [
            {
                "agent_id": agent.agent_id,
                "company_id": agent.company_id,
                "user_id": agent.user_id,
                "status": agent.status,
                "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
                "platform": agent.platform,
                "hostname": agent.hostname
            }
            for agent in agents
        ]
    }


@router.post("/create-task")
async def create_task(task_data: dict, request: Request, db: Session = Depends(get_db)):
    """
    Create task (called by web app - no agent auth required).
    Tasks are pushed to user-specific Redis queue: 'agent:{user_id}'
    """
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    user_id = task_data.get('user_id')
    task_type = task_data.get('task_type')
    parameters = task_data.get('parameters', {})
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    task_id = str(uuid.uuid4())
    
    agent_service = AgentService(db)
    db_task = agent_service.create_celery_task(
        task_id=task_id,
        company_id=company_id,
        user_id=user_id,
        task_type=task_type,
        parameters=parameters
    )
    
    # Add to user-specific Redis queue
    queue_name = f'agent:{user_id}'
    redis_message = json.dumps({
        'task_id': task_id,
        'task_type': task_type,
        'company_id': company_id,
        'user_id': user_id
    })
    redis_client.rpush(queue_name, redis_message)
    
    return {"success": True, "task_id": task_id, "queue": queue_name}


@router.get("/task-status/{task_id}")
async def get_task_status_endpoint(task_id: str, request: Request, db: Session = Depends(get_db)):
    """Get task status (for dashboard - no agent auth required)."""

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    agent_service = AgentService(db)
    db_task = agent_service.get_celery_task(task_id)

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user["type"] != "super_admin" and db_task.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "task_id": task_id,
        "task_type": db_task.task_type,
        "status": db_task.status,
        "result": db_task.result,
        "error_message": db_task.error_message,
        "agent_id": db_task.agent_id,
        "created_at": db_task.created_at.isoformat() if db_task.created_at else None,
        "started_at": db_task.started_at.isoformat() if db_task.started_at else None,
        "completed_at": db_task.completed_at.isoformat() if db_task.completed_at else None
    }


@router.get("/queue-stats")
async def get_queue_stats(request: Request, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get queue statistics (for admin dashboard)."""
    try:

        current_user = get_current_user_from_request(request)
        company_id = current_user["company_id"]

        if user_id:
            queue_name = f'agent:{user_id}'
            queue_length = redis_client.llen(queue_name)
            return {"user_id": user_id, "queue": queue_name, "queue_length": queue_length}
        else:
            all_queues = []
            cursor = 0
            total_tasks = 0
            
            while True:
                cursor, keys = redis_client.scan(cursor, match='agent:*', count=100)
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    length = redis_client.llen(key)
                    total_tasks += length
                    if length > 0:
                        all_queues.append({"queue": key, "length": length})
                if cursor == 0:
                    break
            
            return {
                "total_queues": len(all_queues),
                "total_pending_tasks": total_tasks,
                "queues_with_tasks": all_queues
            }
    except redis.RedisError as e:
        return {"error": str(e)}


@router.post("/regenerate-api-key")
async def regenerate_api_key_endpoint(
    data: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Regenerate API key for an agent (from web dashboard).
    This also regenerates the session_id, invalidating all existing JWTs.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    agent_id = data.get('agent_id')
    user_id = data.get('user_id')
    
    if not agent_id or not user_id:
        raise HTTPException(status_code=400, detail="agent_id and user_id required")
    
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not owned by user")
    if current_user["type"] != "super_admin" and agent.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Regenerate both API key and session
    agent.api_key = generate_api_key()
    agent.current_session_id = generate_session_id()
    db.commit()
    
    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": agent.api_key,
        "message": "API key and session regenerated. Agent must re-register."
    }
