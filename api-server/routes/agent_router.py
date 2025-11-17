# Agent API Router - Direct Redis (No Celery for Agent Tasks)
# Location: api-server/routes/agent_router.py

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import redis
import json
import os
import uuid

from models.database import get_db
from models.agent_models import Agent, AgentTask
from services.agent_service import AgentService

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL)


@router.post("/register")
async def register_agent(
    agent_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Register agent"""
    agent_service = AgentService(db)
    agent = agent_service.register_agent(
        agent_id=agent_data.get('agent_id'),
        company_id=agent_data.get('company_id'),
        user_id=agent_data.get('user_id'),
        hostname=agent_data.get('hostname'),
        platform=agent_data.get('platform'),
        version=agent_data.get('version', '2.0.0')
    )
    return {"success": True, "agent_id": agent.agent_id}


@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Receive heartbeat"""
    agent_service = AgentService(db)
    agent_service.update_heartbeat(
        agent_id=heartbeat_data.get('agent_id'),
        status=heartbeat_data.get('status', 'idle'),
        current_task_id=heartbeat_data.get('current_task_id')
    )
    return {"success": True}


@router.get("/poll-task")
async def poll_task(
    agent_id: str,
    company_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Agent polls for tasks from Redis agent_only queue
    Simple direct Redis access - no Celery parsing needed
    """
    try:
        # Pop task from Redis list (LPOP gets oldest task)
        task_data = redis_client.lpop('agent_only')
        
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
        
    except redis.RedisError as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")


@router.post("/task-result")
async def update_task_result(
    result_data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Agent sends task result"""
    task_id = result_data.get('task_id')
    status = result_data.get('status')
    result = result_data.get('result')
    error = result_data.get('error')
    
    # Update database
    agent_service = AgentService(db)
    agent_service.update_celery_task_result(task_id=task_id, status=status, result=result, error=error)
    
    return {"success": True}


@router.post("/task-progress")
async def update_task_progress(progress_data: dict, authorization: str = Header(None)):
    """Agent sends progress updates"""
    # Just acknowledge - could log to database if needed
    return {"success": True}


@router.get("/agents")
async def list_agents(company_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all agents"""
    agent_service = AgentService(db)
    agents = agent_service.get_agents(company_id=company_id)
    return {
        "agents": [
            {
                "agent_id": agent.agent_id,
                "company_id": agent.company_id,
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
    Create task (called by web app OR by Celery crawl tasks)
    Direct Redis - no Celery for agent tasks
    """
    company_id = task_data.get('company_id')
    user_id = task_data.get('user_id')
    task_type = task_data.get('task_type')
    parameters = task_data.get('parameters', {})
    
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
    
    # Add to Redis queue (simple JSON message)
    redis_message = json.dumps({
        'task_id': task_id,
        'task_type': task_type,
        'company_id': company_id,
        'user_id': user_id
    })
    redis_client.rpush('agent_only', redis_message)
    
    return {"success": True, "task_id": task_id, "message": "Task queued successfully"}


@router.get("/task-status/{task_id}")
async def get_task_status_endpoint(task_id: str, db: Session = Depends(get_db)):
    """Get task status from database"""
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
async def get_queue_stats():
    """Get queue statistics"""
    try:
        agent_queue_length = redis_client.llen('agent_only')
        return {
            "agent_queue_length": agent_queue_length,
            "agent_queue": "agent_only"
        }
    except redis.RedisError as e:
        return {"error": str(e)}