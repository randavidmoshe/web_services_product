# ============================================================================
# Form Mapper - SQLAlchemy Models
# ============================================================================
# Models for form_mapper_sessions, form_map_results, form_mapper_session_logs
# ============================================================================

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    Numeric, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database import Base


class FormMapperSession(Base):
    """
    Tracks each form mapping session.
    Links to a form_page_route discovered by Form Pages Locator.
    """
    __tablename__ = "form_mapper_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to discovered form page
    form_page_route_id = Column(Integer, ForeignKey("form_page_routes.id", ondelete="CASCADE"), nullable=True)
    test_page_route_id = Column(Integer, ForeignKey("test_page_routes.id", ondelete="CASCADE"), nullable=True)
    # Ownership
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Agent assignment
    agent_id = Column(String(100), nullable=True)
    
    # Session configuration
    config = Column(JSON, default=dict)
    
    # State machine status
    status = Column(String(50), nullable=False, default="pending")
    
    # Progress tracking
    current_step_index = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    steps_executed = Column(Integer, default=0)
    
    # Junction discovery
    current_path_number = Column(Integer, default=1)
    total_paths_discovered = Column(Integer, default=0)
    
    # Error tracking
    consecutive_failures = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # AI budget tracking
    ai_calls_count = Column(Integer, default=0)
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_estimate = Column(Numeric(10, 4), default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    form_page_route = relationship("FormPageRoute", back_populates="mapper_sessions")
    results = relationship("FormMapResult", back_populates="session", cascade="all, delete-orphan")
    logs = relationship("FormMapperSessionLog", back_populates="session", cascade="all, delete-orphan")
    test_page_route = relationship("TestPageRoute", back_populates="mapper_sessions")
    
    # Status constants
    STATUS_PENDING = "pending"
    STATUS_INITIALIZING = "initializing"
    STATUS_EXTRACTING_DOM = "extracting_dom"
    STATUS_GENERATING_STEPS = "generating_steps"
    STATUS_EXECUTING = "executing"
    STATUS_RECOVERING = "recovering"
    STATUS_REGENERATING = "regenerating"
    STATUS_VERIFYING_UI = "verifying_ui"
    STATUS_COMPLETING = "completing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "form_page_route_id": self.form_page_route_id,
            "test_page_route_id": self.test_page_route_id,
            "network_id": self.network_id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "config": self.config,
            "status": self.status,
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "steps_executed": self.steps_executed,
            "current_path_number": self.current_path_number,
            "total_paths_discovered": self.total_paths_discovered,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "ai_calls_count": self.ai_calls_count,
            "ai_tokens_used": self.ai_tokens_used,
            "ai_cost_estimate": float(self.ai_cost_estimate) if self.ai_cost_estimate else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FormMapResult(Base):
    """
    Stores the final mapping result for a form page path.
    Multiple results per form_page_route (one per junction path).
    """
    __tablename__ = "form_map_results"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Links
    form_mapper_session_id = Column(Integer, ForeignKey("form_mapper_sessions.id", ondelete="CASCADE"), nullable=False)
    form_page_route_id = Column(Integer, ForeignKey("form_page_routes.id", ondelete="CASCADE"), nullable=True)
    test_page_route_id = Column(Integer, ForeignKey("test_page_routes.id", ondelete="CASCADE"), nullable=True)

    # Test scenario (if mapped with scenario)
    test_scenario_id = Column(Integer, ForeignKey("form_page_test_scenarios.id", ondelete="SET NULL"), nullable=True)
    
    # Ownership (denormalized)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, nullable=True)
    
    # Path info
    path_number = Column(Integer, default=1)
    path_junctions = Column(JSON, default=list)
    
    # Main result: test steps
    steps = Column(JSON, nullable=False, default=list)
    
    # Extracted form structure
    form_fields = Column(JSON, default=list)
    field_relationships = Column(JSON, default=list)
    
    # UI issues
    ui_issues = Column(JSON, default=list)
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verification_errors = Column(JSON, default=list)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    session = relationship("FormMapperSession", back_populates="results")
    form_page_route = relationship("FormPageRoute", back_populates="map_results")
    test_page_route = relationship("TestPageRoute", back_populates="map_results")
    test_scenario = relationship("FormPageTestScenario", back_populates="map_results")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "form_mapper_session_id": self.form_mapper_session_id,
            "form_page_route_id": self.form_page_route_id,
            "test_page_route_id": self.test_page_route_id,
            "test_scenario_id": self.test_scenario_id,
            "test_scenario_name": self.test_scenario.name if self.test_scenario else None,
            "network_id": self.network_id,
            "company_id": self.company_id,
            "path_number": self.path_number,
            "path_junctions": self.path_junctions,
            "steps": self.steps,
            "steps_count": len(self.steps) if self.steps else 0,
            "form_fields": self.form_fields,
            "field_relationships": self.field_relationships,
            "ui_issues": self.ui_issues,
            "is_verified": self.is_verified,
            "verification_errors": self.verification_errors,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_steps_by_test_case(self, test_case: str) -> List[Dict]:
        """Get steps filtered by test_case"""
        if not self.steps:
            return []
        return [s for s in self.steps if s.get("test_case") == test_case]
    
    def get_junction_steps(self) -> List[Dict]:
        """Get steps marked as junctions"""
        if not self.steps:
            return []
        return [s for s in self.steps if s.get("junction")]


class FormMapperSessionLog(Base):
    """
    Detailed event log for a mapping session.
    Used for debugging and monitoring.
    """
    __tablename__ = "form_mapper_session_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    session_id = Column(Integer, ForeignKey("form_mapper_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Event info
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    session = relationship("FormMapperSession", back_populates="logs")
    
    # Event type constants
    EVENT_STATE_CHANGE = "state_change"
    EVENT_TASK_QUEUED = "task_queued"
    EVENT_TASK_COMPLETED = "task_completed"
    EVENT_AI_CALL = "ai_call"
    EVENT_STEP_EXECUTED = "step_executed"
    EVENT_ERROR = "error"
    EVENT_ALERT_DETECTED = "alert_detected"
    EVENT_DOM_CHANGED = "dom_changed"
    EVENT_UI_ISSUE = "ui_issue"
    EVENT_JUNCTION_FOUND = "junction_found"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



class FormPageTestScenario(Base):
    """
    Test scenarios for form mapping.
    Each scenario contains field values to use during mapping.
    """
    __tablename__ = "form_page_test_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    form_page_route_id = Column(Integer, ForeignKey("form_page_routes.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    form_page_route = relationship("FormPageRoute", back_populates="test_scenarios")
    map_results = relationship("FormMapResult", back_populates="test_scenario")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "form_page_route_id": self.form_page_route_id,
            "name": self.name,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# Add relationships to existing models (if not already present)
# ============================================================================
# 
# In your existing FormPageRoute model, add:
#
# mapper_sessions = relationship("FormMapperSession", back_populates="form_page_route")
# map_results = relationship("FormMapResult", back_populates="form_page_route")
#
# ============================================================================
