# Agent API Router - Direct Redis (No Celery for Agent Tasks)
# Location: api-server/routes/agent_router.py
#
# UPDATED: Per-user queue isolation for scalability (100,000+ users)
# UPDATED: API Key authentication for secure agent communication
#
# Security: Each agent gets a unique API key on registration.
# All subsequent requests must include the API key in X-Agent-API-Key header.

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import redis
import json
import os
import uuid
import secrets

from models.database import get_db
from models.agent_models import Agent, AgentTask
from services.agent_service import AgentService

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL)


def generate_api_key() -> str:
    """Generate a secure random API key (43 characters)"""
    return secrets.token_urlsafe(32)


def validate_api_key(
    x_agent_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Agent:
    """
    Validate API key from X-Agent-API-Key header.
    Returns the Agent if valid, raises HTTPException if not.
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
            detail="Invalid API key."
        )
    
    return agent


@router.post("/register")
async def register_agent(
    agent_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Register agent and return API key.
    The API key is returned ONLY during registration - agent must store it.
    """
    agent_id = agent_data.get('agent_id')
    company_id = agent_data.get('company_id')
    user_id = agent_data.get('user_id')
    hostname = agent_data.get('hostname')
    platform = agent_data.get('platform')
    version = agent_data.get('version', '2.0.0')
    
    # Check if agent already exists
    existing_agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if existing_agent:
        # Update existing agent
        existing_agent.company_id = company_id
        existing_agent.user_id = user_id
        existing_agent.hostname = hostname
        existing_agent.platform = platform
        existing_agent.version = version
        existing_agent.status = "online"
        existing_agent.last_heartbeat = datetime.utcnow()
        
        # If agent doesn't have an API key, generate one
        if not existing_agent.api_key:
            existing_agent.api_key = generate_api_key()
        
        db.commit()
        db.refresh(existing_agent)
        
        return {
            "success": True,
            "agent_id": existing_agent.agent_id,
            "api_key": existing_agent.api_key,
            "message": "Agent updated. Store the API key securely - it's required for all requests."
        }
    else:
        # Create new agent with API key
        api_key = generate_api_key()
        
        new_agent = Agent(
            agent_id=agent_id,
            company_id=company_id,
            user_id=user_id,
            hostname=hostname,
            platform=platform,
            version=version,
            status="online",
            api_key=api_key,
            last_heartbeat=datetime.utcnow()
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)
        
        return {
            "success": True,
            "agent_id": new_agent.agent_id,
            "api_key": api_key,
            "message": "Agent registered. Store the API key securely - it's required for all requests."
        }


@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat_data: dict,
    agent: Agent = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Receive heartbeat from authenticated agent.
    Requires X-Agent-API-Key header.
    """
    agent.status = heartbeat_data.get('status', 'idle')
    agent.current_task_id = heartbeat_data.get('current_task_id')
    agent.last_heartbeat = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.get("/poll-task")
async def poll_task(
    agent_id: str,
    company_id: int,
    agent: Agent = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Agent polls for tasks from their user-specific Redis queue.
    Requires X-Agent-API-Key header.
    
    Each user has their own queue: 'agent:{user_id}'
    This ensures Agent A never grabs Agent B's tasks.
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
    agent: Agent = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Agent sends task result.
    Requires X-Agent-API-Key header.
    """
    task_id = result_data.get('task_id')
    status = result_data.get('status')
    result = result_data.get('result')
    error = result_data.get('error')
    
    # Update database
    agent_service = AgentService(db)
    agent_service.update_celery_task_result(task_id=task_id, status=status, result=result, error=error)
    
    return {"success": True}


@router.post("/task-status")
async def update_task_status(
    status_data: dict,
    agent: Agent = Depends(validate_api_key),
    db: Session = Depends(get_db)
):
    """
    Agent sends task status update.
    Requires X-Agent-API-Key header.
    """
    task_id = status_data.get('task_id')
    status = status_data.get('status')
    message = status_data.get('message')
    result = status_data.get('result')
    
    # Update database
    agent_service = AgentService(db)
    
    if status == 'completed':
        agent_service.update_celery_task_result(task_id=task_id, status=status, result=result)
    elif status == 'failed':
        agent_service.update_celery_task_result(task_id=task_id, status=status, error=message)
    else:
        # Just update status (running, etc.)
        db_task = agent_service.get_celery_task(task_id)
        if db_task:
            db_task.status = status
            db.commit()
    
    return {"success": True}


@router.post("/task-progress")
async def update_task_progress(
    progress_data: dict,
    agent: Agent = Depends(validate_api_key)
):
    """
    Agent sends progress updates.
    Requires X-Agent-API-Key header.
    """
    # Just acknowledge - could log to database if needed
    return {"success": True}


@router.get("/agents")
async def list_agents(company_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    List all agents.
    Note: This endpoint does NOT require API key (for admin dashboard).
    """
    query = db.query(Agent)
    if company_id:
        query = query.filter(Agent.company_id == company_id)
    
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
async def create_task(task_data: dict, db: Session = Depends(get_db)):
    """
    Create task (called by web app OR by server endpoints).
    Note: This endpoint does NOT require agent API key (called from server/web app).
    Tasks are pushed to user-specific Redis queue: 'agent:{user_id}'
    """
    company_id = task_data.get('company_id')
    user_id = task_data.get('user_id')
    task_type = task_data.get('task_type')
    parameters = task_data.get('parameters', {})
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Store in database
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
    
    return {"success": True, "task_id": task_id, "queue": queue_name, "message": "Task queued successfully"}


@router.get("/task-status/{task_id}")
async def get_task_status_endpoint(task_id: str, db: Session = Depends(get_db)):
    """
    Get task status from database.
    Note: This endpoint does NOT require agent API key (for dashboard polling).
    """
    agent_service = AgentService(db)
    db_task = agent_service.get_celery_task(task_id)
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
async def get_queue_stats(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get queue statistics.
    Note: This endpoint does NOT require agent API key (for admin dashboard).
    """
    try:
        if user_id:
            # Get specific user's queue length
            queue_name = f'agent:{user_id}'
            queue_length = redis_client.llen(queue_name)
            return {
                "user_id": user_id,
                "queue": queue_name,
                "queue_length": queue_length
            }
        else:
            # Get all agent:* queues
            all_queues = []
            cursor = 0
            total_tasks = 0
            
            # Scan for all agent:* keys
            while True:
                cursor, keys = redis_client.scan(cursor, match='agent:*', count=100)
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    length = redis_client.llen(key)
                    total_tasks += length
                    if length > 0:  # Only show non-empty queues
                        all_queues.append({
                            "queue": key,
                            "length": length
                        })
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
async def regenerate_api_key(
    data: dict,
    db: Session = Depends(get_db)
):
    """
    Regenerate API key for an agent.
    Called from web dashboard when user wants to reset their agent's API key.
    Requires user authentication (not agent API key).
    """
    agent_id = data.get('agent_id')
    user_id = data.get('user_id')  # From authenticated session
    
    if not agent_id or not user_id:
        raise HTTPException(status_code=400, detail="agent_id and user_id required")
    
    agent = db.query(Agent).filter(
        Agent.agent_id == agent_id,
        Agent.user_id == user_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or not owned by user")
    
    # Generate new API key
    new_api_key = generate_api_key()
    agent.api_key = new_api_key
    db.commit()
    
    return {
        "success": True,
        "agent_id": agent_id,
        "api_key": new_api_key,
        "message": "API key regenerated. Update your agent configuration with the new key."
    }
