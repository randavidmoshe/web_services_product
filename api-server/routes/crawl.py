from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, CrawlSession, Network
from datetime import datetime
from tasks.crawl_tasks import discover_form_pages_task, analyze_form_details_task
from celery.result import AsyncResult

router = APIRouter()

@router.post("/discover-forms")
async def discover_forms(
    project_id: int,
    network_id: int, 
    user_id: int,
    company_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Queue a form discovery job
    Returns immediately with task_id
    Client can poll for status using /crawl/status/{task_id}
    """
    
    # Get network URL
    network = db.query(Network).filter(Network.id == network_id).first()
    if not network:
        raise HTTPException(404, "Network not found")
    
    # Create crawl session
    session = CrawlSession(
        company_id=company_id,
        product_id=product_id,
        project_id=project_id,
        network_id=network_id,
        user_id=user_id,
        session_type="discover_form_pages",
        status="queued"  # Changed from "pending" to "queued"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Queue the task (non-blocking)
    task = discover_form_pages_task.delay(
        session_id=session.id,
        network_url=network.url,
        company_id=company_id,
        product_id=product_id,
        user_id=user_id
    )
    
    return {
        "session_id": session.id,
        "task_id": task.id,
        "status": "queued",
        "message": "Crawl job queued. Use task_id to check status."
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check status of a queued task
    """
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting in queue...'
        }
    elif task.state == 'PROGRESS':
        response = {
            'state': task.state,
            'progress': task.info.get('progress', 0),
            'status': task.info.get('status', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'status': 'Task completed!',
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': 'Task failed',
            'error': str(task.info)
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
    
    return response


@router.post("/analyze-form")
async def analyze_form_details(
    form_page_id: int,
    company_id: int,
    product_id: int,
    user_id: int
):
    """
    Queue form analysis job (Part 2)
    """
    task = analyze_form_details_task.delay(
        form_page_id=form_page_id,
        company_id=company_id,
        product_id=product_id,
        user_id=user_id
    )
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Form analysis queued"
    }


@router.get("/queue-stats")
async def get_queue_stats():
    """
    Get queue statistics
    """
    from celery_app import celery
    
    # Get active tasks
    inspect = celery.control.inspect()
    active = inspect.active()
    scheduled = inspect.scheduled()
    reserved = inspect.reserved()
    
    return {
        "active_tasks": active,
        "scheduled_tasks": scheduled,
        "reserved_tasks": reserved
    }

