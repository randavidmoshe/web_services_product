"""
Activity Logs API Router
Location: api-server/routes/activity_logs.py

Endpoints for receiving and serving activity log entries from agents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from models.database import get_db, ActivityLogEntry, CrawlSession
from models.form_mapper_models import FormMapperSession

router = APIRouter(prefix="/api/activity-logs", tags=["Activity Logs"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LogEntryCreate(BaseModel):
    """Single log entry from agent."""
    timestamp: str
    level: str
    category: str = "milestone"
    message: str
    extra_data: Optional[dict] = None


class ActivityLogBatch(BaseModel):
    """Batch of log entries from agent."""
    activity_type: str  # 'discovery', 'mapping', 'test_run'
    session_id: int
    project_id: int
    company_id: int
    user_id: Optional[int] = None
    entries: List[LogEntryCreate]


class LogEntryResponse(BaseModel):
    """Log entry for API response."""
    id: int
    timestamp: str
    level: str
    category: str
    message: str
    extra_data: Optional[dict] = None
    
    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Summary of an activity session for list view."""
    session_id: int
    activity_type: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    entry_count: int
    has_errors: bool
    summary: Optional[str] = None


class ActivityLogsListResponse(BaseModel):
    """Response for activity logs list."""
    sessions: List[SessionSummary]
    total: int
    page: int
    page_size: int


class ActivityLogDetailResponse(BaseModel):
    """Response for single session's log entries."""
    session_id: int
    activity_type: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    entries: List[LogEntryResponse]
    total_entries: int
    page: int
    page_size: int


# ============================================================================
# POST Endpoint - Receive logs from agent
# ============================================================================

@router.post("")
async def receive_activity_logs(
    batch: ActivityLogBatch,
    db: Session = Depends(get_db)
):
    """
    Receive a batch of log entries from agent.
    Called when activity completes.
    """
    try:
        # Determine which session ID field to use
        crawl_session_id = None
        mapper_session_id = None
        test_run_id = None
        
        if batch.activity_type == "discovery":
            crawl_session_id = batch.session_id
        elif batch.activity_type == "mapping":
            mapper_session_id = batch.session_id
        elif batch.activity_type == "test_run":
            test_run_id = batch.session_id
        
        # Create log entries
        entries_created = 0
        for entry_data in batch.entries:
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(entry_data.timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
            
            entry = ActivityLogEntry(
                company_id=batch.company_id,
                project_id=batch.project_id,
                user_id=batch.user_id,
                activity_type=batch.activity_type,
                crawl_session_id=crawl_session_id,
                mapper_session_id=mapper_session_id,
                test_run_id=test_run_id,
                timestamp=timestamp,
                level=entry_data.level,
                category=entry_data.category,
                message=entry_data.message,
                extra_data=entry_data.extra_data
            )
            db.add(entry)
            entries_created += 1
        
        db.commit()
        
        return {
            "success": True,
            "entries_created": entries_created,
            "activity_type": batch.activity_type,
            "session_id": batch.session_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save logs: {str(e)}")


# ============================================================================
# GET Endpoints - Retrieve logs for frontend
# ============================================================================

@router.get("")
async def list_activity_sessions(
    project_id: int,
    activity_type: Optional[str] = None,
    days: int = Query(default=7, le=90),
    has_errors: Optional[bool] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    List activity sessions for a project.
    Returns summary info for each session.
    """
    # Calculate date cutoff
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query - get distinct sessions
    # We'll query CrawlSession for discovery sessions
    sessions = []
    
    # Get discovery sessions
    if activity_type is None or activity_type == "discovery":
        discovery_query = db.query(CrawlSession).filter(
            CrawlSession.project_id == project_id,
            CrawlSession.created_at >= cutoff_date
        ).order_by(desc(CrawlSession.created_at))
        
        for cs in discovery_query.limit(limit).all():
            # Count log entries for this session
            entry_count = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.crawl_session_id == cs.id
            ).count()
            
            # Check for errors
            error_count = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.crawl_session_id == cs.id,
                ActivityLogEntry.level == 'error'
            ).count()
            
            if has_errors is not None:
                if has_errors and error_count == 0:
                    continue
                if not has_errors and error_count > 0:
                    continue
            
            sessions.append(SessionSummary(
                session_id=cs.id,
                activity_type="discovery",
                status=cs.status or "unknown",
                started_at=cs.started_at.isoformat() if cs.started_at else None,
                completed_at=cs.completed_at.isoformat() if cs.completed_at else None,
                entry_count=entry_count,
                has_errors=error_count > 0,
                summary=f"{cs.forms_found or 0} forms found" if cs.status == "completed" else cs.error_message
            ))
    
    # Get mapping sessions (if FormMapperSession model exists)
    # TODO: Add similar logic for mapping sessions

    # Get mapping sessions
    if activity_type is None or activity_type == "mapping":
        try:
            from models.database import FormPageRoute  # or wherever it's defined

            mapping_query = db.query(FormMapperSession).join(
                FormPageRoute, FormMapperSession.form_page_route_id == FormPageRoute.id
            ).filter(
                FormPageRoute.project_id == project_id,
                FormMapperSession.created_at >= cutoff_date
            ).order_by(desc(FormMapperSession.created_at))

            for ms in mapping_query.limit(limit).all():
                # Count log entries for this session
                entry_count = db.query(ActivityLogEntry).filter(
                    ActivityLogEntry.mapper_session_id == ms.id
                ).count()

                # Check for errors
                error_count = db.query(ActivityLogEntry).filter(
                    ActivityLogEntry.mapper_session_id == ms.id,
                    ActivityLogEntry.level == 'error'
                ).count()

                if has_errors is not None:
                    if has_errors and error_count == 0:
                        continue
                    if not has_errors and error_count > 0:
                        continue

                # Build summary based on status
                if ms.status == "completed":
                    summary = f"{ms.total_paths_discovered or 0} paths mapped"
                elif ms.status == "cancelled":
                    summary = "Cancelled"
                elif ms.status == "failed":
                    summary = ms.last_error or "Failed"
                else:
                    summary = ms.status or "In progress"

                sessions.append(SessionSummary(
                    session_id=ms.id,
                    activity_type="mapping",
                    status=ms.status or "unknown",
                    started_at=ms.created_at.isoformat() if ms.created_at else None,
                    completed_at=ms.completed_at.isoformat() if ms.completed_at else None,
                    entry_count=entry_count,
                    has_errors=error_count > 0,
                    summary=summary
                ))
        except Exception as e:
            # FormMapperSession might not exist in all deployments
            print(f"Warning: Could not load mapping sessions: {e}")

    # Sort all sessions by date (newest first)
    sessions.sort(key=lambda x: x.started_at or "", reverse=True)

    # Pagination
    offset = (page - 1) * limit
    paginated_sessions = sessions[offset:offset + limit]
    
    return ActivityLogsListResponse(
        sessions=paginated_sessions,
        total=len(sessions),
        page=page,
        page_size=limit
    )


@router.get("/{session_type}/{session_id}")
async def get_session_logs(
    session_type: str,
    session_id: int,
    level: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db)
):
    """
    Get log entries for a specific session.
    
    session_type: 'discovery', 'mapping', or 'test_run'
    session_id: The session ID
    """
    # Build filter based on session type
    if session_type == "discovery":
        session_filter = ActivityLogEntry.crawl_session_id == session_id
        # Get session info
        session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        status = session.status
        started_at = session.started_at.isoformat() if session.started_at else None
        completed_at = session.completed_at.isoformat() if session.completed_at else None

    elif session_type == "mapping":
        session_filter = ActivityLogEntry.mapper_session_id == session_id
        # Get FormMapperSession info
        session = db.query(FormMapperSession).filter(FormMapperSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        status = session.status or "unknown"
        started_at = session.created_at.isoformat() if session.created_at else None
        completed_at = session.completed_at.isoformat() if hasattr(session,
                                                                   'completed_at') and session.completed_at else None
        
    elif session_type == "test_run":
        session_filter = ActivityLogEntry.test_run_id == session_id
        status = "unknown"
        started_at = None
        completed_at = None
        
    else:
        raise HTTPException(status_code=400, detail="Invalid session type")
    
    # Build query
    query = db.query(ActivityLogEntry).filter(session_filter)
    
    if level:
        query = query.filter(ActivityLogEntry.level == level)
    
    # Get total count
    total = query.count()
    
    # Get paginated entries
    offset = (page - 1) * limit
    entries = query.order_by(ActivityLogEntry.timestamp).offset(offset).limit(limit).all()
    
    return ActivityLogDetailResponse(
        session_id=session_id,
        activity_type=session_type,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        entries=[
            LogEntryResponse(
                id=e.id,
                timestamp=e.timestamp.isoformat() if e.timestamp else "",
                level=e.level,
                category=e.category,
                message=e.message,
                extra_data=e.extra_data
            ) for e in entries
        ],
        total_entries=total,
        page=page,
        page_size=limit
    )
