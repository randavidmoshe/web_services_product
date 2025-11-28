# Agent Database Models
# Location: web_services_product/api-server/models/agent_models.py
#
# UPDATED: Added api_key field for Part 2 authentication

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from models.database import Base


class Agent(Base):
    """
    Represents an agent running on customer's network
    """
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # API Key for authentication (Part 2)
    api_key = Column(String(64), unique=True, index=True, nullable=True)
    
    # Agent info
    hostname = Column(String(255))
    platform = Column(String(50))
    version = Column(String(20))
    
    # Status
    status = Column(String(20), default='offline')
    current_task_id = Column(String(100), nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'hostname': self.hostname,
            'platform': self.platform,
            'version': self.version,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AgentTask(Base):
    """
    Represents a task to be executed by an agent
    """
    __tablename__ = "agent_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Ownership
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    agent_id = Column(String(100), ForeignKey('agents.agent_id'), nullable=True)
    
    # Task details
    task_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    
    # Status
    status = Column(String(20), default='pending')
    
    # Results
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'task_type': self.task_type,
            'parameters': self.parameters,
            'status': self.status,
            'result': self.result,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
