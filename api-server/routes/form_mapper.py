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
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, FormPageRoute
from models.form_mapper_models import FormMapperSession, FormMapResult, FormMapperSessionLog
from services.form_mapper_orchestrator import FormMapperOrchestrator, SessionStatus
from celery.result import AsyncResult
from celery_app import celery
import os

import redis as redis_lib
import json as json_lib

# Module-level shared connection pool for API endpoints
_api_redis_pool = redis_lib.ConnectionPool(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    max_connections=20
)

from sqlalchemy.orm.attributes import flag_modified
from celery_app import celery
from utils.auth_helpers import get_current_user_from_request

from routes.agent_router import validate_jwt_and_session
from models.agent_models import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/form-mapper", tags=["Form Mapper"])


# ============================================================================
# Request/Response Models
# ============================================================================

class StartMappingRequest(BaseModel):
    """Request to start form mapping"""
    form_page_route_id: int
    test_cases: List[dict]  # [{test_id, test_name, description}, ...]
    user_id: Optional[int] = None  # Deprecated - now from token
    company_id: Optional[int] = None  # Deprecated - now from token
    network_id: Optional[int] = None
    agent_id: Optional[str] = None
    config: Optional[dict] = None  # Optional config overrides
    test_scenario_id: Optional[int] = None  # If provided, use scenario for mapping


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
# Completed Paths Response Models
# ============================================================================

class JunctionChoiceResponse(BaseModel):
    """Junction choice in a path"""
    junction_id: Optional[str] = None
    junction_name: str
    option: str
    selector: Optional[str] = None


class CompletedPathResponse(BaseModel):
    """A completed mapping path"""
    id: int
    path_number: int
    path_junctions: List[JunctionChoiceResponse]
    steps: List[dict]
    steps_count: int
    is_verified: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    test_scenario_id: Optional[int] = None
    test_scenario_name: Optional[str] = None


class CompletedPathsListResponse(BaseModel):
    """List of completed paths for a form page route"""
    form_page_route_id: int
    total_paths: int
    paths: List[CompletedPathResponse]

class ContinueMappingRequest(BaseModel):
    """Request to continue mapping from existing paths"""
    user_id: int
    company_id: Optional[int] = None
    network_id: Optional[int] = None
    agent_id: Optional[str] = None
    test_cases: List[dict]
    config: Optional[dict] = None


class ContinueMappingResponse(BaseModel):
    """Response after starting continue mapping"""
    session_id: Optional[str] = None
    status: str
    message: str
    all_paths_complete: bool = False


class StepUpdateRequest(BaseModel):
    """Request to update a step"""
    action: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None

# ============================================================================
# User Endpoints
# ============================================================================

@router.post("/start", response_model=StartMappingResponse, status_code=202)
async def start_form_mapping(
    body: StartMappingRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start mapping a form page.
    
    This creates a new mapping session and queues the initial task
    to the agent. Returns immediately with session_id.
    """
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]
    user_id = current_user["user_id"]
    network_id = body.network_id
    print(f"[DEBUG] start_form_mapping: network_id from body = {network_id}")
    
    # Validate form_page_route exists
    form_page_route = db.query(FormPageRoute).filter(
        FormPageRoute.id == body.form_page_route_id
    ).first()
    
    if not form_page_route:
        raise HTTPException(status_code=404, detail="Form page route not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page_route.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Use network_id from request, or fall back to form_page_route.network_id
    if not network_id:
        network_id = form_page_route.network_id

    # Validate test_cases
    if not body.test_cases:
        raise HTTPException(status_code=400, detail="At least one test case is required")
    
    # Get or assign agent
    agent_id = body.agent_id
    if not agent_id:
        # Use default agent assignment logic
        agent_id = f"agent-{user_id}"  # Simplified - you may have more complex logic

    # Cleanup old form files from S3 and DB before remap
    if form_page_route.project_id and company_id:
        celery.send_task(
            'tasks.cleanup_form_s3_files',
            kwargs={
                'company_id': company_id,
                'project_id': form_page_route.project_id,
                'form_page_route_id': body.form_page_route_id,
                'reason': 'remap'
            }
        )
        logger.info(f"[API] Queued cleanup of old form files for route {body.form_page_route_id}")

    # Create orchestrator and session
    orchestrator = FormMapperOrchestrator(db)
    
    # Write result to Redis for Celery worker
    try:
        # First create database record to get integer ID
        db_session = FormMapperSession(
            form_page_route_id=body.form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            agent_id=agent_id,
            status="initializing",
            config=body.config or {}
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # Now create Redis session with the database ID
        session = orchestrator.create_session(
            session_id=str(db_session.id),
            form_page_route_id=body.form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            config=body.config,
            test_cases=body.test_cases,
            test_scenario_id=body.test_scenario_id
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
        # CloudWatch logging
        try:
            from services.session_logger import get_session_logger, ActivityType
            log = get_session_logger(
                db_session=db,
                activity_type=ActivityType.MAPPING.value,
                session_id=str(db_session.id) if 'db_session' in locals() and db_session else "unknown",
                company_id=company_id if 'company_id' in locals() else None,
                user_id=user_id if 'user_id' in locals() else None
            )
            msg = f"!!!! ❌ Error starting mapping: {e}"
            print(msg)
            log.error(msg, category="error")
        except:
            pass
        # If session was created, properly fail it and close agent
        if 'db_session' in locals() and db_session.id:
            from tasks.form_mapper_tasks import sync_mapper_session_status
            sync_mapper_session_status.delay(str(db_session.id), "failed", f"Start error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/routes/{form_page_route_id}/continue-mapping", response_model=ContinueMappingResponse, status_code=202)
async def continue_form_mapping(
        form_page_route_id: int,
        body: ContinueMappingRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Continue mapping a form page from existing paths.

    Loads existing paths from DB, asks AI if more paths needed.
    If yes - starts full mapping flow with junction instructions.
    If no - returns immediately with all_paths_complete=True.
    """
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]
    user_id = current_user["user_id"]
    network_id = body.network_id

    # Validate form_page_route exists
    form_page_route = db.query(FormPageRoute).filter(
        FormPageRoute.id == form_page_route_id
    ).first()

    if not form_page_route:
        raise HTTPException(status_code=404, detail="Form page route not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page_route.company_id:
        raise HTTPException(status_code=403, detail="Access denied")


    if not network_id:
        network_id = form_page_route.network_id

    # Check if there are existing paths
    existing_paths = db.query(FormMapResult).filter(
        FormMapResult.form_page_route_id == form_page_route_id
    ).order_by(FormMapResult.path_number).all()

    if not existing_paths:
        raise HTTPException(status_code=400, detail="No existing paths found. Use /start for initial mapping.")

    # Validate test_cases
    if not body.test_cases:
        raise HTTPException(status_code=400, detail="At least one test case is required")

    agent_id = body.agent_id
    if not agent_id:
        agent_id = f"agent-{user_id}"

    # Build completed_paths for AI evaluation (same format as _load_junction_paths_from_db)
    config = body.config or {}
    max_options_for_junction = config.get("max_options_for_junction", 8)

    completed_paths_for_ai = []
    for result in existing_paths:
        steps = result.steps or []
        path_junctions = []
        for step in steps:
            if step.get("is_junction"):
                junction_info = step.get("junction_info", {})
                all_options = junction_info.get("all_options", [])
                if len(all_options) > max_options_for_junction:
                    continue
                path_junctions.append({
                    "name": junction_info.get("junction_name", "unknown"),
                    "chosen_option": junction_info.get("chosen_option") or step.get("value"),
                    "all_options": all_options
                })
        completed_paths_for_ai.append({
            "path_number": result.path_number,
            "junctions": path_junctions
        })

    logger.info(f"[API] Continue mapping: {len(completed_paths_for_ai)} existing paths for route {form_page_route_id}")

    try:
        # Create DB session record
        db_session = FormMapperSession(
            form_page_route_id=form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            agent_id=agent_id,
            status="initializing",
            config=body.config or {}
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)

        # Create Redis session
        orchestrator = FormMapperOrchestrator(db)
        orchestrator.create_session(
            session_id=str(db_session.id),
            form_page_route_id=form_page_route_id,
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            config=body.config,
            test_cases=body.test_cases,
            skip_cleanup=True
        )

        # Transition to evaluating state
        from services.form_mapper_orchestrator import MapperState
        orchestrator.transition_to(str(db_session.id), MapperState.CONTINUE_MAPPING_EVALUATING)

        # Get config for AI evaluation
        max_paths = config.get("max_junction_paths", 7)
        discover_all = config.get("ai_discover_all_path_combinations", False)

        # Trigger Celery task to evaluate existing paths
        from tasks.form_mapper_tasks import evaluate_existing_paths
        evaluate_existing_paths.delay(
            session_id=str(db_session.id),
            completed_paths=completed_paths_for_ai,
            discover_all_combinations=discover_all,
            max_paths=max_paths
        )

        logger.info(
            f"[API] Continue mapping session {db_session.id} created, evaluating {len(completed_paths_for_ai)} paths")

        return ContinueMappingResponse(
            session_id=str(db_session.id),
            status="evaluating",
            message=f"Evaluating {len(completed_paths_for_ai)} existing paths to determine if more mapping needed.",
            all_paths_complete=False
        )

    except Exception as e:
        logger.error(f"[API] Error starting continue mapping: {e}", exc_info=True)
        if 'db_session' in locals() and db_session.id:
            from tasks.form_mapper_tasks import sync_mapper_session_status
            sync_mapper_session_status.delay(str(db_session.id), "failed", f"Continue mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-sessions")
async def get_active_mapping_sessions(
        request: Request,
        db: Session = Depends(get_db)
):
    """Get all active mapping sessions for the current user."""
    current_user = get_current_user_from_request(request)
    token_company_id = current_user["company_id"]

    active_sessions = db.query(FormMapperSession).filter(
        FormMapperSession.company_id == token_company_id,
        FormMapperSession.status.in_(['initializing', 'pending', 'running'])
    ).all()

    return [
        {
            "session_id": session.id,
            "form_page_route_id": session.form_page_route_id,
            "test_page_route_id": session.test_page_route_id,
            "status": session.status
        }
        for session in active_sessions
    ]


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    request: Request,
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
        FormMapperSession.id == int(session_id)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != session.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
            FormMapResult.form_mapper_session_id == int(session_id)
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
        request: Request,
        db: Session = Depends(get_db)
):
    """Cancel a mapping session."""
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != session.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the final result of a completed mapping session."""
    # Get session
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != session.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    form_page_route_id: Optional[int] = Query(None, description="Filter by form page route"),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List mapping sessions."""
    current_user = get_current_user_from_request(request)
    token_company_id = current_user["company_id"]

    query = db.query(FormMapperSession).filter(FormMapperSession.company_id == token_company_id)
    
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
    request: Request,
    form_page_route_id: Optional[int] = Query(None, description="Filter by form page route"),
    network_id: Optional[int] = Query(None, description="Filter by network"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List mapping results."""
    current_user = get_current_user_from_request(request)
    token_company_id = current_user["company_id"]

    query = db.query(FormMapResult).filter(FormMapResult.company_id == token_company_id)
    
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
    body: AgentTaskResultRequest,
    agent: Agent = Depends(validate_jwt_and_session),
    db: Session = Depends(get_db)
):
    """
    Agent reports task result.
    
    This endpoint is called by the desktop agent after completing
    a task. The orchestrator processes the result and determines
    the next action.
    """

    session_id = body.session_id
    
    # Verify session exists
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify this agent's user owns this session
    if session.user_id != agent.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build result dict for orchestrator
    result = {
        "task_type": body.task_type,
        "success": body.success,
        "error": body.error,
        **body.payload
    }
    logger.info(
        f"[API] AGENT_TASK_RESULT: session={session_id}, task_type={body.task_type}, success={body.success}, payload_keys={list(body.payload.keys())}")
    orchestrator = FormMapperOrchestrator(db)

    # Write result to Redis for Celery worker (using shared pool)
    api_redis = redis_lib.Redis(connection_pool=_api_redis_pool, decode_responses=True)
    result_key = f"runner_step_result:{session_id}"
    api_redis.setex(result_key, 300, json_lib.dumps(result))
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
        # CloudWatch logging
        try:
            from services.session_logger import get_session_logger, ActivityType
            log = get_session_logger(
                db_session=db,
                activity_type=ActivityType.MAPPING.value,
                session_id=str(session_id),
                company_id=session.company_id if session else None,
                user_id=session.user_id if session else None
            )
            msg = f"!!!! ❌ Error processing agent result: {e}"
            print(msg)
            log.error(msg, category="error")
        except:
            pass
        # Properly fail session and close agent
        from tasks.form_mapper_tasks import sync_mapper_session_status
        sync_mapper_session_status.delay(session_id, "failed", f"Server error: {str(e)}")
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
        handle_validation_error_recovery,
        verify_ui_visual,
        regenerate_steps,
        regenerate_verify_steps,
        evaluate_paths_with_ai,
        save_mapping_result,
        verify_junction_visual,
        verify_page_visual,
        trigger_visual_page_screenshot,
        verify_dynamic_step_visual
    )
    
    task_map = {
        "analyze_form_page": analyze_form_page,
        "analyze_failure_and_recover": analyze_failure_and_recover,
        "handle_alert_recovery": handle_alert_recovery,
        "handle_validation_error_recovery": handle_validation_error_recovery,
        "verify_ui_visual": verify_ui_visual,
        "regenerate_steps": regenerate_steps,
        "regenerate_verify_steps": regenerate_verify_steps,
        "evaluate_paths_with_ai": evaluate_paths_with_ai,
        "save_mapping_result": save_mapping_result,
        "verify_junction_visual": verify_junction_visual,
        "verify_page_visual": verify_page_visual,
        "trigger_visual_page_screenshot": trigger_visual_page_screenshot,
        "verify_dynamic_step_visual": verify_dynamic_step_visual
    }
    
    task = task_map.get(task_name)
    if task:
        task.delay(**celery_args)
    else:
        msg = f"!!!! ❌ Unknown Celery task requested: {task_name}"
        print(msg)
        logger.error(f"[API] Unknown Celery task requested: {task_name}")
        # CloudWatch logging
        session_id = celery_args.get("session_id")
        if session_id:
            try:
                from services.session_logger import get_session_logger, ActivityType
                log = get_session_logger(
                    db_session=None,
                    activity_type=ActivityType.MAPPING.value,
                    session_id=str(session_id),
                    company_id=None,
                    user_id=None
                )
                log.error(msg, category="error")
            except:
                pass
        raise ValueError(f"Unknown Celery task: {task_name}")


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/results/{result_id}/download")
async def download_result(
    result_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Download result as JSON file (like path_1_create_verify_person.json)."""
    result = db.query(FormMapResult).filter(
        FormMapResult.id == result_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != result.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return steps as JSON
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        content=result.steps,
        headers={
            "Content-Disposition": f"attachment; filename=path_{result.path_number}_form_{result.form_page_route_id}.json"
        }
    )


# ============================================================================
# Completed Paths Endpoints (for Frontend Display)
# ============================================================================

@router.get("/routes/{form_page_route_id}/paths", response_model=CompletedPathsListResponse)
async def get_completed_paths(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Get all completed mapping paths for a form page route.

    Each path represents a unique combination of junction options
    that was discovered during form mapping.

    Returns paths with steps (junction info filtered out for display).
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    ## Query all form_map_results for this form_page_route
    #results = db.query(FormMapResult).filter(
    #    FormMapResult.form_page_route_id == form_page_route_id
    #).order_by(FormMapResult.path_number.asc()).all()

    # Query all form_map_results for this form_page_route
    from sqlalchemy.orm import joinedload
    query_filter = FormMapResult.form_page_route_id == form_page_route_id
    if current_user["type"] != "super_admin":
        query_filter = query_filter & (FormMapResult.company_id == company_id)

    results = db.query(FormMapResult).options(
        joinedload(FormMapResult.test_scenario)
    ).filter(query_filter).order_by(FormMapResult.path_number.asc()).all()

    paths = []
    for result in results:
        # Parse path_junctions - handle different storage formats
        junctions = []
        path_junctions_data = result.path_junctions or []

        # Handle dict format with junction_choices key
        if isinstance(path_junctions_data, dict):
            junction_choices = path_junctions_data.get('junction_choices', {})
            if isinstance(junction_choices, dict):
                # Convert {junction_id: option} to list format
                for jid, opt in junction_choices.items():
                    junctions.append(JunctionChoiceResponse(
                        junction_id=jid,
                        junction_name=jid.replace('junction_', ''),
                        option=opt
                    ))
            elif isinstance(junction_choices, list):
                for j in junction_choices:
                    if isinstance(j, dict):
                        junctions.append(JunctionChoiceResponse(
                            junction_id=j.get('junction_id'),
                            junction_name=j.get('junction_name', ''),
                            option=j.get('option', ''),
                            selector=j.get('selector')
                        ))
        elif isinstance(path_junctions_data, list):
            for j in path_junctions_data:
                if isinstance(j, dict):
                    junctions.append(JunctionChoiceResponse(
                        junction_id=j.get('junction_id'),
                        junction_name=j.get('junction_name', ''),
                        option=j.get('option', ''),
                        selector=j.get('selector')
                    ))

        # Filter junction info from steps for display
        filtered_steps = []
        for step in (result.steps or []):
            step_copy = dict(step)
            step_copy.pop('is_junction', None)
            step_copy.pop('junction_info', None)
            filtered_steps.append(step_copy)

        paths.append(CompletedPathResponse(
            id=result.id,
            path_number=result.path_number or 1,
            path_junctions=junctions,
            steps=filtered_steps,
            steps_count=len(result.steps) if result.steps else 0,
            is_verified=result.is_verified or False,
            created_at=result.created_at.isoformat() if result.created_at else None,
            updated_at=result.updated_at.isoformat() if result.updated_at else None,
            test_scenario_id=result.test_scenario_id,
            test_scenario_name=result.test_scenario.name if result.test_scenario else None
        ))

    return CompletedPathsListResponse(
        form_page_route_id=form_page_route_id,
        total_paths=len(paths),
        paths=paths
    )


@router.delete("/paths/{path_id}")
async def delete_path(
        path_id: int,
        request: Request,
        db: Session = Depends(get_db),
):
    """
    Delete a specific mapping path.

    Scalability notes:
    - DB deletion is atomic
    - If path has S3 assets, cleanup is queued to Celery (non-blocking)
    """
    # Find the path
    result = db.query(FormMapResult).filter(FormMapResult.id == path_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Path not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != result.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Store info for potential S3 cleanup before deletion
    form_page_route_id = result.form_page_route_id
    path_number = result.path_number

    # Check if there's an active mapping session for this form (prevent deletion during mapping)
    active_session = db.query(FormMapperSession).filter(
        FormMapperSession.form_page_route_id == form_page_route_id,
        FormMapperSession.status == SessionStatus.RUNNING
    ).first()

    if active_session:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete path while mapping is in progress"
        )

    # Delete from DB
    db.delete(result)
    db.commit()

    logger.info(f"[API] Deleted path {path_id} (path_number={path_number}) from form_page_route {form_page_route_id}")

    return {
        "message": "Path deleted successfully",
        "path_id": path_id,
        "form_page_route_id": form_page_route_id
    }


@router.get("/routes/paths-counts")
async def get_paths_counts(
        request: Request,
        form_page_route_ids: str = Query(..., description="Comma-separated form page route IDs"),
        db: Session = Depends(get_db)
):
    """Get path counts for multiple form pages at once (scalable batch query)"""
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]
    from sqlalchemy import func

    ids = [int(id.strip()) for id in form_page_route_ids.split(",") if id.strip()]

    if not ids:
        return {}

    query_filter = FormMapResult.form_page_route_id.in_(ids)
    if current_user["type"] != "super_admin":
        query_filter = query_filter & (FormMapResult.company_id == company_id)

    counts = db.query(
        FormMapResult.form_page_route_id,
        func.count(FormMapResult.id)
    ).filter(query_filter).group_by(FormMapResult.form_page_route_id).all()

    return {str(route_id): count for route_id, count in counts}


@router.put("/paths/{path_id}/steps")
async def update_all_path_steps(
        path_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """Replace all steps for a path"""
    result = db.query(FormMapResult).filter(FormMapResult.id == path_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Path not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != result.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    steps = body.get("steps", [])
    result.steps = steps

    db.commit()
    db.refresh(result)

    return {"success": True, "message": "All steps updated", "steps_count": len(steps)}


@router.put("/paths/{path_id}/steps/{step_index}")
async def update_path_step(
        path_id: int,
        step_index: int,
        step_update: StepUpdateRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Update a specific step in a completed path.

    Used by frontend to allow editing of step details
    (selector, value, description).
    """
    # Get the form_map_result
    result = db.query(FormMapResult).filter(
        FormMapResult.id == path_id
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Path not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != result.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Validate step_index
    if not result.steps or step_index < 0 or step_index >= len(result.steps):
        raise HTTPException(status_code=400, detail=f"Invalid step index: {step_index}")

    # Create new steps list (JSON columns need full replacement)
    steps = list(result.steps)
    step = dict(steps[step_index])

    # Apply updates (only non-None fields)
    if step_update.action is not None:
        step['action'] = step_update.action
    if step_update.selector is not None:
        step['selector'] = step_update.selector
    if step_update.value is not None:
        step['value'] = step_update.value
    if step_update.description is not None:
        step['description'] = step_update.description

    steps[step_index] = step
    result.steps = steps

    db.commit()
    db.refresh(result)

    logger.info(f"[API] Updated step {step_index} in path {path_id}")

    return {
        "success": True,
        "message": f"Step {step_index} updated successfully",
        "step": step
    }


@router.get("/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: str,
    request: Request,
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
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != session.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
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


# ============================================================================
# Field Assist Endpoints
# ============================================================================

class FieldAssistRequest(BaseModel):
    """Request for field assist query"""
    session_id: str
    screenshot_base64: str
    step: dict
    query_type: str  # "dropdown_visible", etc.
    rail_bounds: Optional[dict] = None
    action_type: Optional[str] = None


@router.post("/field-assist")
async def start_field_assist_query(
        body: FieldAssistRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Start a field assist query (async via Celery).
    Returns task_id for polling.
    """
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    # Verify session belongs to user's company
    session = db.query(FormMapperSession).filter(
        FormMapperSession.id == body.session_id
    ).first()
    if session and current_user["type"] != "super_admin" and session.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from tasks.form_mapper_tasks import field_assist_query

    task = field_assist_query.delay(
        session_id=body.session_id,
        screenshot_base64=body.screenshot_base64,
        step=body.step,
        query_type=body.query_type,
        rail_bounds=body.rail_bounds,
        action_type=body.action_type
    )

    return {"task_id": task.id, "status": "pending"}


@router.get("/field-assist/{task_id}")
async def get_field_assist_result(task_id: str, request: Request):
    """
    Get field assist query result by task_id.
    """
    get_current_user_from_request(request)
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "status": result.state.lower()
    }

    if result.state == 'SUCCESS':
        response["status"] = "completed"
        response["result"] = result.result
    elif result.state == 'FAILURE':
        response["status"] = "failed"
        response["error"] = str(result.info) if result.info else 'Unknown error'

    return response

@router.post("/pom/generate")
async def start_pom_generation(
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Start POM generation task
    Returns task_id for polling
    """

    form_page_route_id = body.get("form_page_route_id")
    language = body.get("language", "python")
    framework = body.get("framework", "selenium")
    style = body.get("style", "basic")

    # Get form page data
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get paths for this form page
    paths = db.query(FormMapResult).filter(
        FormMapResult.form_page_route_id == form_page_route_id
    ).all()

    if not paths:
        raise HTTPException(status_code=400, detail="No paths found for this form page. Map the form first.")

    # Prepare data for task
    form_page_data = {
        "form_name": form_page.form_name,
        "url": form_page.url,
        "navigation_steps": form_page.navigation_steps or []
    }

    paths_data = []
    for path in paths:
        paths_data.append({
            "path_number": path.path_number,
            "path_junctions": path.path_junctions,
            "steps": path.steps
        })

    # Queue the task
    task = celery.send_task(
        'tasks.generate_pom',
        kwargs={
            'form_page_data': form_page_data,
            'paths_data': paths_data,
            'language': language,
            'framework': framework,
            'style': style,
            'company_id': current_user["company_id"],
            'product_id': 1
        }
    )

    return {"task_id": task.id, "status": "pending"}


@router.get("/pom/tasks/{task_id}")
async def get_pom_task_status(task_id: str, request: Request):
    """
    Get POM generation task status and result
    """
    get_current_user_from_request(request)
    from celery_app import celery

    result = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "status": result.state.lower()
    }

    if result.state == 'PROCESSING':
        response["progress"] = result.info.get('progress', 0) if result.info else 0
        response["message"] = result.info.get('message', '') if result.info else ''
    elif result.state == 'SUCCESS':
        response["status"] = "completed"
        response["code"] = result.result.get('code', '') if result.result else ''
        response["language"] = result.result.get('language', '') if result.result else ''
        response["framework"] = result.result.get('framework', '') if result.result else ''
    elif result.state == 'FAILURE':
        response["status"] = "failed"
        response["error"] = str(result.info) if result.info else 'Unknown error'

    return response

# ============================================================================
# Spec Document Endpoints
# ============================================================================

@router.post("/routes/{form_page_route_id}/spec")
async def upload_spec_document(
        form_page_route_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Upload or replace spec document for a form page
    Request body: {filename, content_type, content}
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    filename = body.get("filename", "spec.txt")
    content_type = body.get("content_type", "text/plain")
    content = body.get("content", "")

    if not content:
        raise HTTPException(status_code=400, detail="Spec content is required")

    form_page.spec_document = {
        "filename": filename,
        "content_type": content_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    form_page.spec_document_content = content
    db.commit()

    return {
        "success": True,
        "message": "Spec document uploaded successfully",
        "spec_document": form_page.spec_document
    }


@router.get("/routes/{form_page_route_id}/spec")
async def get_spec_document(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Get spec document for a form page
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not form_page.spec_document:
        return {"spec_document": None, "content": None}

    return {
        "spec_document": form_page.spec_document,
        "content": form_page.spec_document_content
    }


@router.put("/routes/{form_page_route_id}/spec")
async def update_spec_document(
        form_page_route_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Update spec document content (edit)
    Request body: {content}
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not form_page.spec_document:
        raise HTTPException(status_code=400, detail="No spec document exists. Upload one first.")

    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Spec content is required")

    form_page.spec_document_content = content
    form_page.spec_document["uploaded_at"] = datetime.utcnow().isoformat()
    # Mark the JSON column as modified
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(form_page, "spec_document")
    db.commit()

    return {
        "success": True,
        "message": "Spec document updated successfully",
        "spec_document": form_page.spec_document
    }


@router.delete("/routes/{form_page_route_id}/spec")
async def delete_spec_document(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Delete spec document for a form page
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    form_page.spec_document = None
    form_page.spec_document_content = None
    db.commit()

    return {
        "success": True,
        "message": "Spec document deleted successfully"
    }


# ============================================================================
# Spec Compliance Generation Endpoints
# ============================================================================

@router.post("/spec-compliance/generate")
async def start_spec_compliance_generation(
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Start spec compliance report generation task
    Returns task_id for polling
    """
    form_page_route_id = body.get("form_page_route_id")

    # Get form page data
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if spec document exists
    if not form_page.spec_document or not form_page.spec_document_content:
        raise HTTPException(status_code=400, detail="No spec document found. Upload a spec first.")

    # Get paths for this form page
    paths = db.query(FormMapResult).filter(
        FormMapResult.form_page_route_id == form_page_route_id
    ).all()

    if not paths:
        raise HTTPException(status_code=400, detail="No paths found for this form page. Map the form first.")

    # Prepare data for task
    form_page_data = {
        "form_name": form_page.form_name,
        "url": form_page.url,
        "navigation_steps": form_page.navigation_steps or []
    }

    paths_data = []
    for path in paths:
        paths_data.append({
            "path_number": path.path_number,
            "path_junctions": path.path_junctions,
            "steps": path.steps
        })

    spec_data = {
        "filename": form_page.spec_document.get("filename", "spec.txt"),
        "content": form_page.spec_document_content
    }

    # Queue the task
    task = celery.send_task(
        'tasks.generate_spec_compliance',
        kwargs={
            'form_page_data': form_page_data,
            'paths_data': paths_data,
            'spec_data': spec_data,
            'company_id': current_user["company_id"],
            'product_id': 1
        }
    )

    return {"task_id": task.id, "status": "pending"}


@router.get("/spec-compliance/tasks/{task_id}")
async def get_spec_compliance_task_status(task_id: str, request: Request):
    """
    Get spec compliance generation task status and result
    """
    get_current_user_from_request(request)
    result = AsyncResult(task_id, app=celery)

    response = {
        "task_id": task_id,
        "status": result.state.lower()
    }

    if result.state == 'PROCESSING':
        response["progress"] = result.info.get('progress', 0) if result.info else 0
        response["message"] = result.info.get('message', '') if result.info else ''
    elif result.state == 'SUCCESS':
        response["status"] = "completed"
        response["report"] = result.result.get('report', '') if result.result else ''
        response["summary"] = result.result.get('summary', {}) if result.result else {}
    elif result.state == 'FAILURE':
        response["status"] = "failed"
        response["error"] = str(result.info) if result.info else 'Unknown error'

    return response

# ============================================================================
# Form Mapper Verification Instructions Endpoints (DB-only)
# ============================================================================

@router.post("/routes/{form_page_route_id}/verification-instructions")
async def upload_verification_instructions(
        form_page_route_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Upload or replace verification instructions for a form page.
    Request body: {filename, content_type, content}
    For PDF/DOCX, content should be base64 encoded - will be extracted server-side.
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    filename = body.get("filename", "verification_instructions.txt")
    content_type = body.get("content_type", "text/plain")
    content = body.get("content", "")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    # Extract text if PDF/DOCX (base64 encoded)
    extracted_content = content
    if content_type in ['application/pdf', 'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        try:
            import base64
            from services.test_page_visual_assets import extract_text_from_file
            file_bytes = base64.b64decode(content)
            extracted_content = extract_text_from_file(file_bytes, content_type, filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

    form_page.verification_file = {
        "filename": filename,
        "content_type": content_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    form_page.verification_file_content = extracted_content
    db.commit()

    return {
        "success": True,
        "message": "Verification instructions uploaded successfully",
        "verification_file": form_page.verification_file
    }


@router.get("/routes/{form_page_route_id}/verification-instructions")
async def get_verification_instructions(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Get verification instructions for a form page"""
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not form_page.verification_file:
        return {"verification_file": None, "content": None}

    return {
        "verification_file": form_page.verification_file,
        "content": form_page.verification_file_content
    }


@router.put("/routes/{form_page_route_id}/verification-instructions")
async def update_verification_instructions(
        form_page_route_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Update verification instructions content (edit).
    Request body: {content}
    """
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not form_page.verification_file:
        raise HTTPException(status_code=400, detail="No verification instructions exist. Upload first.")

    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    form_page.verification_file_content = content
    form_page.verification_file["uploaded_at"] = datetime.utcnow().isoformat()
    flag_modified(form_page, "verification_file")
    db.commit()

    return {
        "success": True,
        "message": "Verification instructions updated successfully",
        "verification_file": form_page.verification_file
    }


@router.delete("/routes/{form_page_route_id}/verification-instructions")
async def delete_verification_instructions(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Delete verification instructions for a form page"""
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    form_page.verification_file = None
    form_page.verification_file_content = None
    db.commit()

    return {
        "success": True,
        "message": "Verification instructions deleted successfully"
    }


# ============================================================================
# Test Scenarios Endpoints
# ============================================================================

@router.get("/routes/{form_page_route_id}/test-scenarios")
async def get_test_scenarios(
        form_page_route_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Get all test scenarios for a form page"""
    current_user = get_current_user_from_request(request)
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from models.form_mapper_models import FormPageTestScenario



    scenarios = db.query(FormPageTestScenario).filter(
        FormPageTestScenario.form_page_route_id == form_page_route_id
    ).order_by(FormPageTestScenario.created_at.desc()).all()

    return {
        "scenarios": [s.to_dict() for s in scenarios]
    }


@router.post("/routes/{form_page_route_id}/test-scenarios")
async def create_test_scenario(
        form_page_route_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """Create a new test scenario"""
    from models.form_mapper_models import FormPageTestScenario

    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    name = body.get("name", "").strip()
    content = body.get("content", "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    scenario = FormPageTestScenario(
        form_page_route_id=form_page_route_id,
        name=name,
        content=content
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return {
        "success": True,
        "scenario": scenario.to_dict()
    }


@router.get("/routes/{form_page_route_id}/test-scenarios/{scenario_id}")
async def get_test_scenario(
        form_page_route_id: int,
        scenario_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Get a specific test scenario"""
    current_user = get_current_user_from_request(request)

    # Verify form_page_route belongs to user's company
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from models.form_mapper_models import FormPageTestScenario

    scenario = db.query(FormPageTestScenario).filter(
        FormPageTestScenario.id == scenario_id,
        FormPageTestScenario.form_page_route_id == form_page_route_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="Test scenario not found")


    return {
        "scenario": scenario.to_dict()
    }


@router.put("/routes/{form_page_route_id}/test-scenarios/{scenario_id}")
async def update_test_scenario(
        form_page_route_id: int,
        scenario_id: int,
        body: dict,
        request: Request,
        db: Session = Depends(get_db)
):
    """Update a test scenario"""
    current_user = get_current_user_from_request(request)

    # Verify form_page_route belongs to user's company
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from models.form_mapper_models import FormPageTestScenario

    scenario = db.query(FormPageTestScenario).filter(
        FormPageTestScenario.id == scenario_id,
        FormPageTestScenario.form_page_route_id == form_page_route_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="Test scenario not found")

    if "name" in body:
        name = body["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        scenario.name = name

    if "content" in body:
        content = body["content"].strip()
        if not content:
            raise HTTPException(status_code=400, detail="Content cannot be empty")
        scenario.content = content

    db.commit()
    db.refresh(scenario)

    return {
        "success": True,
        "scenario": scenario.to_dict()
    }


@router.delete("/routes/{form_page_route_id}/test-scenarios/{scenario_id}")
async def delete_test_scenario(
        form_page_route_id: int,
        scenario_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """Delete a test scenario"""
    current_user = get_current_user_from_request(request)

    # Verify form_page_route belongs to user's company
    form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    if not form_page:
        raise HTTPException(status_code=404, detail="Form page not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != form_page.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from models.form_mapper_models import FormPageTestScenario

    scenario = db.query(FormPageTestScenario).filter(
        FormPageTestScenario.id == scenario_id,
        FormPageTestScenario.form_page_route_id == form_page_route_id
    ).first()

    if not scenario:
        raise HTTPException(status_code=404, detail="Test scenario not found")

    #form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
    #if form_page:
    #   verify_company_access(authorization, form_page.company_id, db)

    db.delete(scenario)
    db.commit()

    return {
        "success": True,
        "message": "Test scenario deleted"
    }