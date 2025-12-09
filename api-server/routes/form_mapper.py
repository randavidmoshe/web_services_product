# ============================================================================
# Form Mapper - API Endpoints
# ============================================================================
# FastAPI router for Form Mapper endpoints:
# - POST /form-mapper/start - Start mapping a form
# - GET /form-mapper/sessions/{id}/status - Get session status
# - POST /form-mapper/sessions/{id}/cancel - Cancel session
# - GET /form-mapper/sessions/{id}/result - Get final result
# - POST /form-mapper/agent/task-result - Agent reports task result
# ============================================================================

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, FormPageRoute
from models.form_mapper_models import FormMapperSession, FormMapResult, FormMapperSessionLog
from services.form_mapper_orchestrator import FormMapperOrchestrator, SessionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/form-mapper", tags=["Form Mapper"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartMappingRequest(BaseModel):
    """Request to start form mapping"""
    form_page_route_id: int
    test_cases: List[dict]  # [{test_id, test_name, description}, ...]
    user_id: int
    company_id: Optional[int] = None
    network_id: Optional[int] = None
    agent_id: Optional[str] = None
    config: Optional[dict] = None  # Optional config overrides


class StartMappingResponse(BaseModel):
    """Response after starting mapping"""
    session_id: str
    status: str
    message: str


class SessionStatusResponse(BaseModel):
    """Session status response"""
    session_id: str
    status: str
    current_step_index: int
    total_steps: int
    steps_executed: int
    ai_calls_count: int
    pending_celery_task: Optional[str] = None
    result_id: Optional[int] = None
    error: Optional[str] = None


class SessionResultResponse(BaseModel):
    """Final result response"""
    session_id: str
    result_id: int
    form_page_route_id: int
    path_number: int
    path_junctions: List[dict]
    steps: List[dict]
    steps_count: int
    form_fields: List[dict]
    field_relationships: List[dict]
    ui_issues: List[str]
    is_verified: bool
    ai_usage: dict
    created_at: str


class AgentTaskResultRequest(BaseModel):
    """Agent reports task result"""
    session_id: str
    task_type: str
    success: bool
    payload: dict  # Task-specific result data
    error: Optional[str] = None


class AgentTaskResultResponse(BaseModel):
    """Response to agent after processing result"""
    status: str
    next_action: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# User Endpoints
# ============================================================================

@router.post("/start", response_model=StartMappingResponse, status_code=202)
async def start_form_mapping(
    request: StartMappingRequest,
    db: Session = Depends(get_db)
):
    """
    Start mapping a form page.
    
    This creates a new mapping session and queues the initial task
    to the agent. Returns immediately with session_id.
    """
    user_id = request.user_id
    network_id = request.network_id
    print(f"[DEBUG] start_form_mapping: network_id from request = {network_id}")
    company_id = request.company_id
    
    # Validate form_page_route exists
    form_page_route = db.query(FormPageRoute).filter(
        FormPageRoute.id == request.form_page_route_id
    ).first()
    
    if not form_page_route:
        raise HTTPException(status_code=404, detail="Form page route not found")
    
    # Validate test_cases
    if not request.test_cases:
        raise HTTPException(status_code=400, detail="At least one test case is required")
    
    # Get or assign agent
    agent_id = request.agent_id
    if not agent_id:
        # Use default agent assignment logic
        agent_id = f"agent-{user_id}"  # Simplified - you may have more complex logic
    
    # Create orchestrator and session
    orchestrator = FormMapperOrchestrator(db)
    
    # Write result to Redis for Celery worker
    try:
        # First create database record to get integer ID
        db_session = FormMapperSession(
            form_page_route_id=request.form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            agent_id=agent_id,
            status="initializing",
            config=request.config or {}
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Now create Redis session with the database ID
        session = orchestrator.create_session(
            session_id=str(db_session.id),  # Use DB integer ID as string
            form_page_route_id=request.form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            config=request.config,
            test_cases=request.test_cases
        )
        
        # Start the mapping process (Login → Navigate → Map)
        result = orchestrator.start_login_phase(
            session_id=str(db_session.id)
        )
        success = result.get("success", False)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start mapping")
        
        logger.info(f"[API] Started mapping session {db_session.id} for user {user_id}")
        
        return StartMappingResponse(
            session_id=str(db_session.id),
            status="initializing",
            message="Mapping started. Agent will begin processing."
        )
        
    except Exception as e:
        logger.error(f"[API] Error starting mapping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-sessions")
async def get_active_mapping_sessions(
        db: Session = Depends(get_db)
):
    """Get all active mapping sessions for the current user."""
    active_sessions = db.query(FormMapperSession).filter(
        FormMapperSession.status.in_(['initializing', 'pending', 'running'])
    ).all()

    return [
        {
            "session_id": session.id,
            "form_page_route_id": session.form_page_route_id,
            "status": session.status
        }
        for session in active_sessions
    ]


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    check_celery: bool = Query(True, description="Check for pending Celery results"),
    db: Session = Depends(get_db)
):
    """
    Get the current status of a mapping session.
    
    If check_celery=True (default), also checks for and processes
    any pending Celery task results.
    """
    # Get session
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    orchestrator = FormMapperOrchestrator(db)
    
    # Check and process any pending Celery results
    if check_celery and session.status not in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
        celery_result = orchestrator.check_and_process_celery_results(session_id)
        if celery_result:
            logger.info(f"[API] Processed Celery result for session {session_id}")
    
    # Get current status
    status = orchestrator.get_session_status(session_id)
    
    # Check if there's a result
    result_id = None
    if session.status == SessionStatus.COMPLETED:
        result = db.query(FormMapResult).filter(
            FormMapResult.form_mapper_session_id == session_id
        ).first()
        if result:
            result_id = result.id
    
    return SessionStatusResponse(
        session_id=session_id,
        status=status.get("status", session.status),
        current_step_index=status.get("current_step_index", session.current_step_index),
        total_steps=status.get("total_steps", session.total_steps),
        steps_executed=status.get("steps_executed", session.steps_executed),
        ai_calls_count=status.get("ai_calls_count", session.ai_calls_count),
        pending_celery_task=status.get("pending_celery_task"),
        result_id=result_id,
        error=session.last_error
    )


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(
        session_id: str,
        db: Session = Depends(get_db)
):
    """Cancel a mapping session."""
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel session with status: {session.status}"
        )

    # Update DB status (for heartbeat to detect)
    session.status = SessionStatus.CANCELLED
    db.commit()

    # Update Redis state
    orchestrator = FormMapperOrchestrator(db)
    orchestrator.cancel_session(session_id)

    logger.info(f"[API] Cancelled mapping session {session_id}")
    return {"status": "cancelled", "session_id": session_id}


@router.get("/sessions/{session_id}/result", response_model=SessionResultResponse)
async def get_session_result(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get the final result of a completed mapping session."""
    # Get session
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Session not completed. Current status: {session.status}"
        )
    
    # Get result
    result = db.query(FormMapResult).filter(
        FormMapResult.form_mapper_session_id == session_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return SessionResultResponse(
        session_id=session_id,
        result_id=result.id,
        form_page_route_id=result.form_page_route_id,
        path_number=result.path_number,
        path_junctions=result.path_junctions or [],
        steps=result.steps or [],
        steps_count=len(result.steps or []),
        form_fields=result.form_fields or [],
        field_relationships=result.field_relationships or [],
        ui_issues=result.ui_issues or [],
        is_verified=result.is_verified,
        ai_usage={
            "calls": session.ai_calls_count,
            "tokens": session.ai_tokens_used,
            "cost_estimate": float(session.ai_cost_estimate or 0)
        },
        created_at=result.created_at.isoformat() if result.created_at else ""
    )


@router.get("/sessions")
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    form_page_route_id: Optional[int] = Query(None, description="Filter by form page route"),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List mapping sessions."""
    query = db.query(FormMapperSession)
    
    if user_id:
        query = query.filter(FormMapperSession.user_id == user_id)
    
    if status:
        query = query.filter(FormMapperSession.status == status)
    
    if form_page_route_id:
        query = query.filter(FormMapperSession.form_page_route_id == form_page_route_id)
    
    total = query.count()
    
    sessions = query.order_by(
        FormMapperSession.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sessions": [s.to_dict() for s in sessions]
    }


@router.get("/results")
async def list_results(
    form_page_route_id: Optional[int] = Query(None, description="Filter by form page route"),
    network_id: Optional[int] = Query(None, description="Filter by network"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List mapping results."""
    query = db.query(FormMapResult)
    
    if form_page_route_id:
        query = query.filter(FormMapResult.form_page_route_id == form_page_route_id)
    
    if network_id:
        query = query.filter(FormMapResult.network_id == network_id)
    
    total = query.count()
    
    results = query.order_by(
        FormMapResult.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [r.to_dict() for r in results]
    }


# ============================================================================
# Agent Endpoint (API Key Auth)
# ============================================================================

@router.post("/agent/task-result", response_model=AgentTaskResultResponse)
async def agent_task_result(
    request: AgentTaskResultRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Agent reports task result.
    
    This endpoint is called by the desktop agent after completing
    a task. The orchestrator processes the result and determines
    the next action.
    """
    # TODO: Add API key validation if needed
    # For now, just process the result
    
    session_id = request.session_id
    
    # Verify session exists
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Build result dict for orchestrator
    result = {
        "task_type": request.task_type,
        "success": request.success,
        "error": request.error,
        **request.payload
    }
    logger.info(
        f"[API] AGENT_TASK_RESULT: session={session_id}, task_type={request.task_type}, success={request.success}, payload_keys={list(request.payload.keys())}")
    orchestrator = FormMapperOrchestrator(db)
    
    # Write result to Redis for Celery worker
    import redis
    import json
    redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    result_key = f"runner_step_result:{session_id}"
    redis_client.setex(result_key, 300, json.dumps(result))
    logger.info(f"[API] Wrote result to Redis: {result_key}")
    
    try:
        response = orchestrator.process_agent_result(session_id, result)
        
        # Trigger Celery task if orchestrator requests it
        if response.get("trigger_celery") and response.get("celery_task"):
            _trigger_celery_task(response.get("celery_task"), response.get("celery_args", {}))
            logger.info(f"[API] Triggered Celery task: {response.get('celery_task')}")
        
        return AgentTaskResultResponse(
            status=response.get("status", "ok"),
            next_action=response.get("next_action"),
            message=response.get("message") or response.get("error")
        )
        
    except Exception as e:
        logger.error(f"[API] Error processing agent result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _trigger_celery_task(task_name: str, celery_args: dict):
    """
    Trigger the appropriate Celery task based on task name.
    
    This dynamically routes to the correct task based on what
    the orchestrator requests.
    """
    from tasks.form_mapper_tasks import (
        analyze_form_page,
        analyze_failure_and_recover,
        handle_alert_recovery,
        verify_ui_visual,
        regenerate_steps,
        save_mapping_result
    )
    
    task_map = {
        "analyze_form_page": analyze_form_page,
        "analyze_failure_and_recover": analyze_failure_and_recover,
        "handle_alert_recovery": handle_alert_recovery,
        "verify_ui_visual": verify_ui_visual,
        "regenerate_steps": regenerate_steps,
        "save_mapping_result": save_mapping_result
    }
    
    task = task_map.get(task_name)
    if task:
        task.delay(**celery_args)
    else:
        logger.error(f"[API] Unknown Celery task requested: {task_name}")
        raise ValueError(f"Unknown Celery task: {task_name}")


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/results/{result_id}/download")
async def download_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Download result as JSON file (like path_1_create_verify_person.json)."""
    result = db.query(FormMapResult).filter(
        FormMapResult.id == result_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Return steps as JSON
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        content=result.steps,
        headers={
            "Content-Disposition": f"attachment; filename=path_{result.path_number}_form_{result.form_page_route_id}.json"
        }
    )


@router.get("/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """Get logs for a mapping session."""
    # Verify session exists
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    query = db.query(FormMapperSessionLog).filter(
        FormMapperSessionLog.session_id == session_id
    )
    
    if event_type:
        query = query.filter(FormMapperSessionLog.event_type == event_type)
    
    logs = query.order_by(
        FormMapperSessionLog.created_at.desc()
    ).limit(limit).all()
    
    return {
        "session_id": session_id,
        "logs": [log.to_dict() for log in logs]
    }
