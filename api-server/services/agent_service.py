# Agent Service - Business Logic
# Location: web_services_product/api-server/services/agent_service.py

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

from models.agent_models import Agent, AgentTask


class AgentService:
    """
    Service layer for agent operations
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== AGENT MANAGEMENT ==========
    
    def register_agent(
        self,
        agent_id: str,
        company_id: int,
        user_id: int,
        hostname: str,
        platform: str,
        version: str = "1.0.0"
    ) -> Agent:
        """
        Register a new agent or update existing agent
        Called when agent starts up
        """
        # Check if agent already exists
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        
        if agent:
            # Update existing agent
            agent.hostname = hostname
            agent.platform = platform
            agent.version = version
            agent.status = 'online'
            agent.last_heartbeat = datetime.utcnow()
            agent.updated_at = datetime.utcnow()
        else:
            # Create new agent
            agent = Agent(
                agent_id=agent_id,
                company_id=company_id,
                user_id=user_id,
                hostname=hostname,
                platform=platform,
                version=version,
                status='online',
                last_heartbeat=datetime.utcnow()
            )
            self.db.add(agent)
        
        self.db.commit()
        self.db.refresh(agent)
        return agent
    
    def update_heartbeat(
        self,
        agent_id: str,
        status: str = 'idle',
        current_task_id: Optional[str] = None
    ):
        """
        Update agent heartbeat
        Called every 30 seconds by agent
        """
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        
        if agent:
            agent.last_heartbeat = datetime.utcnow()
            agent.status = status
            self.db.commit()
    
    def get_agents(self, company_id: Optional[int] = None) -> List[Agent]:
        """
        Get list of agents
        Optionally filter by company
        """
        query = self.db.query(Agent)
        
        if company_id:
            query = query.filter(Agent.company_id == company_id)
        
        return query.all()
    
    def mark_offline_agents(self, timeout_minutes: int = 2):
        """
        Mark agents as offline if no heartbeat received
        Run this periodically (e.g., every minute)
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        self.db.query(Agent).filter(
            Agent.last_heartbeat < cutoff_time,
            Agent.status != 'offline'
        ).update({
            'status': 'offline'
        })
        
        self.db.commit()
    
    # ========== TASK MANAGEMENT (OLD - DATABASE POLLING) ==========
    
    def create_task(
        self,
        company_id: int,
        user_id: int,
        task_type: str,
        parameters: dict
    ) -> AgentTask:
        """
        Create a new task for an agent
        Called by web app when user runs a test
        """
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        task = AgentTask(
            task_id=task_id,
            company_id=company_id,
            user_id=user_id,
            task_type=task_type,
            parameters=parameters,
            status='pending'
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_pending_task(self, company_id: Optional[int] = None) -> Optional[AgentTask]:
        """
        Get next pending task
        Called by agent during polling
        """
        query = self.db.query(AgentTask).filter(
            AgentTask.status == 'pending'
        ).order_by(AgentTask.created_at.asc())
        
        if company_id:
            query = query.filter(AgentTask.company_id == company_id)
        
        return query.first()
    
    def assign_task_to_agent(self, task_id: int, agent_id: str):
        """
        Assign a task to an agent
        Called when agent picks up a task
        """
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        
        if task:
            task.agent_id = agent_id
            task.status = 'assigned'
            self.db.commit()
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        message: Optional[str] = None,
        result: Optional[dict] = None
    ):
        """
        Update task status
        Called by agent when task starts, completes, or fails
        """
        task = self.db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
        
        if not task:
            return
        
        task.status = status
        
        if status == 'running' and not task.started_at:
            task.started_at = datetime.utcnow()
        
        if status in ['completed', 'failed']:
            task.completed_at = datetime.utcnow()
            task.result = result
            
            if status == 'failed' and message:
                task.error_message = message
        
        self.db.commit()
    
    def get_task(self, task_id: str) -> Optional[AgentTask]:
        """
        Get task by ID
        """
        return self.db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
    
    def get_tasks(
        self,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentTask]:
        """
        Get list of tasks
        """
        query = self.db.query(AgentTask)
        
        if company_id:
            query = query.filter(AgentTask.company_id == company_id)
        
        if user_id:
            query = query.filter(AgentTask.user_id == user_id)
        
        if status:
            query = query.filter(AgentTask.status == status)
        
        return query.order_by(AgentTask.created_at.desc()).limit(limit).all()
    
    # ========== CELERY TASK MANAGEMENT (NEW - REDIS/CELERY) ==========
    
    def create_celery_task(
        self,
        task_id: str,
        company_id: int,
        user_id: int,
        task_type: str,
        parameters: dict
    ) -> AgentTask:
        """
        Create database record for Celery task
        (Actual task is in Redis, this is just for tracking)
        """
        task = AgentTask(
            task_id=task_id,  # Use Celery task ID
            company_id=company_id,
            user_id=user_id,
            task_type=task_type,
            parameters=parameters,
            status='pending'
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def assign_celery_task_to_agent(self, task_id: str, agent_id: str):
        """Assign Celery task to agent in database"""
        task = self.db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
        
        if task:
            task.agent_id = agent_id
            task.status = 'assigned'
            task.started_at = datetime.utcnow()
            self.db.commit()
    
    def update_celery_task_result(
        self,
        task_id: str,
        status: str,
        result: Optional[dict] = None,
        error: Optional[str] = None
    ):
        """Update Celery task result in database"""
        task = self.db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
        
        if task:
            task.status = status
            
            if status == 'completed':
                task.completed_at = datetime.utcnow()
                task.result = result
            elif status == 'failed':
                task.completed_at = datetime.utcnow()
                task.error_message = error
            
            self.db.commit()
    
    def get_celery_task(self, task_id: str) -> Optional[AgentTask]:
        """Get Celery task from database"""
        return self.db.query(AgentTask).filter(AgentTask.task_id == task_id).first()
    
    def get_celery_tasks(
        self,
        company_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentTask]:
        """Get list of Celery tasks"""
        query = self.db.query(AgentTask)
        
        if company_id:
            query = query.filter(AgentTask.company_id == company_id)
        
        if user_id:
            query = query.filter(AgentTask.user_id == user_id)
        
        if status:
            query = query.filter(AgentTask.status == status)
        
        return query.order_by(AgentTask.created_at.desc()).limit(limit).all()
