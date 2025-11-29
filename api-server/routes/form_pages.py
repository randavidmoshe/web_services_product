# Form Pages Routes - API Endpoints for Form Discovery
# Location: web_services_product/api-server/routes/form_pages.py
#
# UPDATED: Added Redis queue integration to trigger agent tasks
# UPDATED: Added AI usage endpoint for dashboard
# UPDATED: Added budget exceeded error handling

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis
import json
import uuid
import os

from models.database import get_db, FormPageRoute, CrawlSession, Network
from models.agent_models import Agent, AgentTask

router = APIRouter()

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL)


# ========== AI USAGE ENDPOINT (for dashboard) ==========

@router.get("/ai-usage")
async def get_ai_usage(
    company_id: int,
    product_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Get AI usage information for dashboard display.
    
    Returns:
        - used: Current usage in dollars (integer)
        - budget: Monthly budget in dollars (integer)
        - is_byok: True if customer uses their own API key
        - reset_date: When budget resets
        - days_until_reset: Days until next reset
    """
    from services.form_pages_locator_service import FormPagesLocatorService
    
    usage = FormPagesLocatorService.get_ai_usage_for_company(db, company_id, product_id)
    return usage


# ========== CRAWL SESSION ENDPOINTS ==========

@router.post("/networks/{network_id}/locate")
async def locate_form_pages(
    network_id: int,
    user_id: int,
    max_depth: int = 20,
    max_form_pages: Optional[int] = None,
    headless: bool = False,
    slow_mode: bool = True,
    ui_verification: bool = True,
    db: Session = Depends(get_db)
):
    """
    Start form page discovery for a network.
    Creates a crawl session, agent task, and pushes to user's Redis queue.
    
    Returns:
        - crawl_session_id: ID to poll for status
        - task_id: Agent task ID
        - status: 'pending'
        
    Raises:
        - 400: No online agent found
        - 402: AI budget exceeded (BUDGET_EXCEEDED)
    """
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    # Verify network exists
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    # Check if user has an online agent
    agent = db.query(Agent).filter(
        Agent.user_id == user_id,
        Agent.status.in_(['online', 'idle', 'busy'])
    ).first()
    
    # Also check heartbeat is recent (within last 2 minutes)
    if agent and agent.last_heartbeat:
        heartbeat_timeout = datetime.utcnow() - timedelta(minutes=2)
        if agent.last_heartbeat < heartbeat_timeout:
            agent = None  # Agent is stale
    
    if not agent:
        raise HTTPException(
            status_code=400, 
            detail="No online agent found. Please ensure your agent is running and connected."
        )
    
    # Initialize service
    service = FormPagesLocatorService(db)
    
    # Prepare crawl task (creates crawl_session) - may raise AIBudgetExceededError
    try:
        task_params = service.prepare_crawl_task(
            network_id=network_id,
            user_id=user_id,
            max_depth=max_depth,
            max_form_pages=max_form_pages,
            headless=headless,
            slow_mode=slow_mode,
            ui_verification=ui_verification
        )
    except AIBudgetExceededError as e:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "AI budget exceeded",
                "message": str(e),
                "code": "BUDGET_EXCEEDED"
            }
        )
    
    if not task_params:
        raise HTTPException(status_code=400, detail="Failed to prepare crawl task")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Create agent_task record in database
    agent_task = AgentTask(
        task_id=task_id,
        company_id=task_params["company_id"],
        user_id=user_id,
        task_type="discover_form_pages",
        parameters=task_params,
        status="pending"
    )
    db.add(agent_task)
    db.commit()
    db.refresh(agent_task)
    
    # Push to user's Redis queue
    queue_name = f'agent:{user_id}'
    redis_message = json.dumps({
        'task_id': task_id,
        'task_type': 'discover_form_pages',
        'company_id': task_params["company_id"],
        'user_id': user_id
    })
    redis_client.rpush(queue_name, redis_message)
    
    return {
        "crawl_session_id": task_params["crawl_session_id"],
        "task_id": task_id,
        "status": "pending",
        "message": "Form page discovery task created and queued",
        "agent_id": agent.agent_id,
        "queue": queue_name
    }


@router.get("/sessions/{session_id}")
async def get_crawl_session(session_id: int, db: Session = Depends(get_db)):
    """Get crawl session status"""
    session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    
    return {
        "id": session.id,
        "status": session.status,
        "pages_crawled": session.pages_crawled,
        "forms_found": session.forms_found,
        "error_message": session.error_message,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }


@router.put("/sessions/{session_id}")
async def update_crawl_session(
    session_id: int,
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Update crawl session status (called by agent)"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    service.update_crawl_session(
        session_id=session_id,
        status=data.get("status"),
        pages_crawled=data.get("pages_crawled"),
        forms_found=data.get("forms_found"),
        error_message=data.get("error_message"),
        error_code=data.get("error_code")
    )
    
    return {"success": True}


@router.get("/sessions/{session_id}/status")
async def get_discovery_status(session_id: int, db: Session = Depends(get_db)):
    """
    Get discovery status including session info, task status, and discovered forms.
    Designed for frontend polling.
    """
    # Get crawl session
    session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    
    # Get discovered forms for this session
    forms = db.query(FormPageRoute).filter(
        FormPageRoute.crawl_session_id == session_id
    ).order_by(FormPageRoute.created_at.desc()).all()
    
    return {
        "session": {
            "id": session.id,
            "status": session.status,
            "pages_crawled": session.pages_crawled,
            "forms_found": session.forms_found,
            "error_message": session.error_message,
            "error_code": session.error_code if hasattr(session, 'error_code') else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None
        },
        "forms": [
            {
                "id": form.id,
                "form_name": form.form_name,
                "url": form.url,
                "navigation_steps": form.navigation_steps,
                "is_root": form.is_root,
                "created_at": form.created_at.isoformat() if form.created_at else None
            }
            for form in forms
        ]
    }


# ========== FORM ROUTES ENDPOINTS ==========

@router.get("/projects/{project_id}/active-sessions")
async def get_active_sessions(project_id: int, db: Session = Depends(get_db)):
    """Get active (pending/running) crawl sessions for a project"""
    sessions = db.query(CrawlSession).filter(
        CrawlSession.project_id == project_id,
        CrawlSession.status.in_(['pending', 'running'])
    ).all()
    
    return [
        {
            "id": s.id,
            "network_id": s.network_id,
            "status": s.status,
            "pages_crawled": s.pages_crawled,
            "forms_found": s.forms_found,
            "started_at": s.started_at.isoformat() if s.started_at else None
        }
        for s in sessions
    ]


@router.get("/routes")
async def list_form_routes(
    network_id: Optional[int] = None,
    project_id: Optional[int] = None,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get form routes with optional filters"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    routes = service.get_form_routes(
        network_id=network_id,
        project_id=project_id,
        company_id=company_id
    )
    
    return [
        {
            "id": r.id,
            "form_name": r.form_name,
            "url": r.url,
            "navigation_steps": r.navigation_steps,
            "id_fields": r.id_fields,
            "is_root": r.is_root,
            "parent_form_route_id": r.parent_form_route_id,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in routes
    ]


@router.post("/routes")
async def create_form_route(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new form route (called by agent)"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    route = service.save_form_route(
        company_id=data.get("company_id"),
        product_id=data.get("product_id"),
        project_id=data.get("project_id"),
        network_id=data.get("network_id"),
        crawl_session_id=data.get("crawl_session_id"),
        form_name=data.get("form_name"),
        url=data.get("url"),
        login_url=data.get("login_url"),
        username=data.get("username"),
        navigation_steps=data.get("navigation_steps", []),
        id_fields=data.get("id_fields", []),
        is_root=data.get("is_root", True),
        verification_attempts=data.get("verification_attempts", 1)
    )
    return route


@router.get("/routes/{route_id}")
async def get_form_route(route_id: int, db: Session = Depends(get_db)):
    """Get a single form route by ID"""
    route = db.query(FormPageRoute).filter(FormPageRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Form route not found")
    return route


@router.put("/routes/{route_id}")
async def update_form_route(
    route_id: int,
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Update a form route (form name and navigation steps)"""
    route = db.query(FormPageRoute).filter(FormPageRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Form route not found")
    
    # Update allowed fields
    if "form_name" in data:
        route.form_name = data["form_name"]
    if "navigation_steps" in data:
        route.navigation_steps = data["navigation_steps"]
    if "url" in data:
        route.url = data["url"]
    if "is_root" in data:
        route.is_root = data["is_root"]
    
    route.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(route)
    
    return {
        "success": True,
        "message": f"Form route {route_id} updated",
        "route": {
            "id": route.id,
            "form_name": route.form_name,
            "url": route.url,
            "navigation_steps": route.navigation_steps,
            "is_root": route.is_root,
            "updated_at": route.updated_at.isoformat() if route.updated_at else None
        }
    }


@router.delete("/routes/{route_id}")
async def delete_form_route(route_id: int, db: Session = Depends(get_db)):
    """Delete a form route"""
    route = db.query(FormPageRoute).filter(FormPageRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Form route not found")
    
    db.delete(route)
    db.commit()
    return {"success": True, "message": f"Form route {route_id} deleted"}


@router.post("/routes/build-hierarchy")
async def build_hierarchy(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Build parent-child relationships for all routes in a network"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    network_id = data.get("network_id")
    if not network_id:
        raise HTTPException(status_code=400, detail="network_id required")
    
    service = FormPagesLocatorService(db)
    service.build_hierarchy(network_id)
    return {"success": True, "message": "Hierarchy built"}


# ========== AI OPERATION ENDPOINTS (called by agent) ==========

@router.post("/ai/login-steps")
async def generate_login_steps(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Generate login automation steps using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    try:
        service._init_ai_helper(company_id, product_id)
    except AIBudgetExceededError as e:
        raise HTTPException(
            status_code=402,
            detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
        )
    
    steps = service.generate_login_steps(
        data.get("page_html"),
        data.get("screenshot_base64"),
        data.get("username"),
        data.get("password")
    )
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "login_steps")
    
    return {"steps": steps}


@router.post("/ai/logout-steps")
async def generate_logout_steps(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Generate logout automation steps using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    try:
        service._init_ai_helper(company_id, product_id)
    except AIBudgetExceededError as e:
        raise HTTPException(
            status_code=402,
            detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
        )
    
    steps = service.generate_logout_steps(
        data.get("page_html"),
        data.get("screenshot_base64")
    )
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "logout_steps")
    
    return {"steps": steps}


@router.post("/ai/form-name")
async def extract_form_name(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Extract semantic form name using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    if company_id and product_id:
        try:
            service._init_ai_helper(company_id, product_id)
        except AIBudgetExceededError as e:
            raise HTTPException(
                status_code=402,
                detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
            )
    
    service.created_form_names = data.get("existing_names", [])
    
    context_data = {
        "url": data.get("url"),
        "url_path": data.get("url_path"),
        "button_clicked": data.get("button_clicked"),
        "page_title": data.get("page_title"),
        "headers": data.get("headers", []),
        "form_labels": data.get("form_labels", [])
    }
    
    form_name = service.extract_form_name(context_data)
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "form_name")
    
    return {"form_name": form_name}


@router.post("/ai/parent-fields")
async def extract_parent_fields(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Extract parent reference fields using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    if company_id and product_id:
        try:
            service._init_ai_helper(company_id, product_id)
        except AIBudgetExceededError as e:
            raise HTTPException(
                status_code=402,
                detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
            )
    
    fields = service.extract_parent_reference_fields(
        data.get("form_name"),
        data.get("page_html"),
        data.get("screenshot_base64")
    )
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "parent_fields")
    
    return {"fields": fields}


@router.post("/ai/ui-defects")
async def verify_ui_defects(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Check for UI defects using AI Vision"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    if company_id and product_id:
        try:
            service._init_ai_helper(company_id, product_id)
        except AIBudgetExceededError as e:
            raise HTTPException(
                status_code=402,
                detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
            )
    
    defects = service.verify_ui_defects(
        data.get("form_name"),
        data.get("screenshot_base64")
    )
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "ui_defects")
    
    return {"defects": defects, "has_defects": bool(defects)}


@router.post("/ai/is-submission-button")
async def is_submission_button(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Determine if button is a form submission button"""
    from services.form_pages_locator_service import FormPagesLocatorService, AIBudgetExceededError
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    crawl_session_id = data.get("crawl_session_id")
    
    if company_id and product_id:
        try:
            service._init_ai_helper(company_id, product_id)
        except AIBudgetExceededError as e:
            raise HTTPException(
                status_code=402,
                detail={"error": "AI budget exceeded", "message": str(e), "code": "BUDGET_EXCEEDED"}
            )
    
    is_submission = service.is_submission_button(data.get("button_text"))
    
    # Track AI cost immediately after call
    if company_id and product_id and user_id:
        service.save_api_usage(company_id, product_id, user_id, crawl_session_id or 0, "is_submission_button")
    
    return {"is_submission": is_submission}


# ========== COST TRACKING ==========

@router.post("/sessions/{session_id}/save-usage")
async def save_api_usage(
    session_id: int,
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Save API usage for a crawl session"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    service._init_ai_helper(data.get("company_id"), data.get("product_id"))
    service.save_api_usage(
        company_id=data.get("company_id"),
        product_id=data.get("product_id"),
        user_id=data.get("user_id"),
        crawl_session_id=session_id
    )
    return {"success": True}
