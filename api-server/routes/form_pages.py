# Form Pages Routes - API Endpoints for Form Discovery
# Location: web_services_product/api-server/routes/form_pages.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from models.database import get_db, FormPageRoute, CrawlSession, Network

router = APIRouter()


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
    Creates a crawl session and returns task parameters for agent.
    """
    from services.form_pages_locator_service import FormPagesLocatorService
    
    # Verify network exists
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    # Initialize service
    service = FormPagesLocatorService(db)
    
    # Prepare crawl task
    task_params = service.prepare_crawl_task(
        network_id=network_id,
        user_id=user_id,
        max_depth=max_depth,
        max_form_pages=max_form_pages,
        headless=headless,
        slow_mode=slow_mode,
        ui_verification=ui_verification
    )
    
    if not task_params:
        raise HTTPException(status_code=400, detail="Failed to prepare crawl task")
    
    return {
        "crawl_session_id": task_params["crawl_session_id"],
        "status": "pending",
        "message": "Form page discovery task created",
        "task_params": task_params
    }


@router.get("/sessions/{session_id}")
async def get_crawl_session(session_id: int, db: Session = Depends(get_db)):
    """Get crawl session status"""
    session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
    return session


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
        error_message=data.get("error_message")
    )
    
    return {"success": True}


# ========== FORM ROUTES ENDPOINTS ==========

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
    return routes


@router.post("/routes")
async def save_form_route(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Save a discovered form route (called by agent)"""
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
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    service._init_ai_helper(data.get("company_id"), data.get("product_id"))
    
    steps = service.generate_login_steps(
        data.get("page_html"),
        data.get("screenshot_base64"),
        data.get("username"),
        data.get("password")
    )
    return {"steps": steps}


@router.post("/ai/logout-steps")
async def generate_logout_steps(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Generate logout automation steps using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    service._init_ai_helper(data.get("company_id"), data.get("product_id"))
    
    steps = service.generate_logout_steps(
        data.get("page_html"),
        data.get("screenshot_base64")
    )
    return {"steps": steps}


@router.post("/ai/form-name")
async def extract_form_name(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Extract semantic form name using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    if company_id and product_id:
        service._init_ai_helper(company_id, product_id)
    
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
    return {"form_name": form_name}


@router.post("/ai/parent-fields")
async def extract_parent_fields(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Extract parent reference fields using AI"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    if company_id and product_id:
        service._init_ai_helper(company_id, product_id)
    
    fields = service.extract_parent_reference_fields(
        data.get("form_name"),
        data.get("page_html"),
        data.get("screenshot_base64")
    )
    return {"fields": fields}


@router.post("/ai/ui-defects")
async def verify_ui_defects(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Check for UI defects using AI Vision"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    if company_id and product_id:
        service._init_ai_helper(company_id, product_id)
    
    defects = service.verify_ui_defects(
        data.get("form_name"),
        data.get("screenshot_base64")
    )
    return {"defects": defects, "has_defects": bool(defects)}


@router.post("/ai/is-submission-button")
async def is_submission_button(
    data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Determine if button is a form submission button"""
    from services.form_pages_locator_service import FormPagesLocatorService
    
    service = FormPagesLocatorService(db)
    company_id = data.get("company_id")
    product_id = data.get("product_id")
    if company_id and product_id:
        service._init_ai_helper(company_id, product_id)
    
    is_submission = service.is_submission_button(data.get("button_text"))
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
