"""
Activity Logs API Router
Location: api-server/routes/activity_logs.py

Endpoints for receiving and serving activity log entries from agents.
Includes screenshot management and download functionality.
"""

import json
import io
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from models.database import get_db, ActivityLogEntry, CrawlSession, ActivityScreenshot, Company
from models.form_mapper_models import FormMapperSession
from services.s3_storage import (
    generate_presigned_put_url,
    generate_presigned_put_urls_batch,
    get_screenshot_presigned_url,
    get_screenshot_download_url,
    get_s3_file_content,
    S3_BUCKET
)

from celery_app import celery
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/api/activity-logs", tags=["Activity Logs"])

# Log size threshold for S3 upload (50KB)
LOG_SIZE_THRESHOLD_BYTES = 50 * 1024


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
    activity_type: str
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
    form_name: Optional[str] = None  # Form page name for mapping sessions


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


# Screenshot models
class ScreenshotUploadRequest(BaseModel):
    """Request for pre-signed upload URLs."""
    activity_type: str  # 'mapping' or 'test_run'
    session_id: int
    project_id: int
    company_id: int
    filenames: List[str]


class ScreenshotUploadResponse(BaseModel):
    """Response with pre-signed URLs."""
    urls: List[dict]  # [{filename, s3_key, url}, ...]
    expires_in: int


class ScreenshotConfirmRequest(BaseModel):
    """Confirm screenshots were uploaded."""
    activity_type: str
    session_id: int
    project_id: int
    company_id: int
    screenshots: List[dict]  # [{s3_key, filename, file_size_bytes}, ...]


class ScreenshotInfo(BaseModel):
    """Screenshot info for API response."""
    id: int
    filename: str
    s3_key: str
    file_size_bytes: Optional[int]
    created_at: str


# Large logs models
class LargeLogUploadRequest(BaseModel):
    """Request for pre-signed URL for large log upload."""
    activity_type: str
    session_id: int
    project_id: int
    company_id: int
    user_id: Optional[int] = None


class LargeLogConfirmRequest(BaseModel):
    """Confirm large log was uploaded to S3."""
    activity_type: str
    session_id: int
    project_id: int
    company_id: int
    user_id: Optional[int] = None
    s3_key: str

class ScreenshotZipConfirmRequest(BaseModel):
    """Confirm screenshot zip was uploaded to S3. Used by Celery method."""
    activity_type: str
    session_id: int
    project_id: int
    company_id: int
    s3_key: str
class FormFilesZipConfirmRequest(BaseModel):
    """Confirm form files zip was uploaded to S3. Used by Celery method."""
    activity_type: str
    session_id: int
    project_id: int
    company_id: int
    form_page_route_id: int
    s3_key: str

# ============================================================================
# POST Endpoint - Receive logs from agent (with Celery)
# ============================================================================

@router.post("")
async def receive_activity_logs(
        batch: ActivityLogBatch,
        db: Session = Depends(get_db)
):
    """
    Receive a batch of log entries from agent.
    Queues to Celery for async processing.
    """
    try:
        # Convert entries to JSON string for Celery
        entries_json = json.dumps([e.dict() for e in batch.entries])
        entries_size = len(entries_json.encode('utf-8'))

        # Check if logs are too large for direct processing
        if entries_size >= LOG_SIZE_THRESHOLD_BYTES:
            return {
                "success": False,
                "error": "logs_too_large",
                "message": f"Log size ({entries_size} bytes) exceeds threshold ({LOG_SIZE_THRESHOLD_BYTES} bytes). Use /logs/upload endpoint.",
                "size_bytes": entries_size,
                "threshold_bytes": LOG_SIZE_THRESHOLD_BYTES
            }

        # Queue to Celery for async processing
        celery.send_task(
            'tasks.process_activity_logs',
            kwargs={
                'entries_json': entries_json,
                'activity_type': batch.activity_type,
                'session_id': batch.session_id,
                'project_id': batch.project_id,
                'company_id': batch.company_id,
                'user_id': batch.user_id
            }
        )

        return {
            "success": True,
            "queued": True,
            "entries_count": len(batch.entries),
            "activity_type": batch.activity_type,
            "session_id": batch.session_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue logs: {str(e)}")


# ============================================================================
# Large Logs - Upload to S3
# ============================================================================

@router.post("/logs/upload")
async def request_log_upload_url(
        request: LargeLogUploadRequest,
        db: Session = Depends(get_db)
):
    """
    Get pre-signed URL for uploading large log file to S3.
    """
    try:
        # Get company's KMS key for BYOK
        company = db.query(Company).filter(Company.id == request.company_id).first()
        kms_key_arn = company.kms_key_arn if company else None

        # Generate S3 key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"logs_temp/{request.company_id}/{request.project_id}/{request.activity_type}_{request.session_id}_{timestamp}.json"

        # Generate pre-signed URL
        url = generate_presigned_put_url(
            s3_key=s3_key,
            content_type='application/json',
            expiration=900,  # 15 minutes
            kms_key_arn=kms_key_arn
        )

        return {
            "success": True,
            "s3_key": s3_key,
            "url": url,
            "expires_in": 900
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.post("/logs/confirm")
async def confirm_log_upload(
        body: LargeLogConfirmRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Confirm large log file was uploaded to S3.
    Queues Celery task to process and insert to DB.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != body.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        # Queue Celery task to read from S3 and insert to DB
        celery.send_task(
            'tasks.process_activity_logs_from_s3',
            kwargs={
                's3_key': body.s3_key,
                'activity_type': body.activity_type,
                'session_id': body.session_id,
                'project_id': body.project_id,
                'company_id': body.company_id,
                'user_id': body.user_id
            }
        )

        return {
            "success": True,
            "queued": True,
            "s3_key": body.s3_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue log processing: {str(e)}")


# ============================================================================
# Screenshot Upload - Pre-signed URLs
# ============================================================================

@router.post("/screenshots/upload")
async def request_screenshot_upload_urls(
        request: ScreenshotUploadRequest,
        db: Session = Depends(get_db)
):
    """
    Get pre-signed URLs for uploading screenshots directly to S3.
    """
    try:
        # Get company's KMS key for BYOK
        company = db.query(Company).filter(Company.id == request.company_id).first()
        kms_key_arn = company.kms_key_arn if company else None

        # Generate S3 keys for each file
        s3_keys = []
        for filename in request.filenames:
            s3_key = f"{request.activity_type}/{request.company_id}/{request.project_id}/{request.session_id}/{filename}"
            s3_keys.append(s3_key)

        # Generate pre-signed URLs
        urls_data = generate_presigned_put_urls_batch(
            s3_keys=s3_keys,
            content_type='image/png',
            expiration=900,
            kms_key_arn=kms_key_arn
        )

        # Add filename to response
        result = []
        for i, url_data in enumerate(urls_data):
            result.append({
                'filename': request.filenames[i],
                's3_key': url_data['s3_key'],
                'url': url_data['url']
            })

        return ScreenshotUploadResponse(
            urls=result,
            expires_in=900
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URLs: {str(e)}")


@router.post("/screenshots/confirm")
async def confirm_screenshot_uploads(
        request: ScreenshotConfirmRequest,
        db: Session = Depends(get_db)
):
    """
    Confirm screenshots were uploaded to S3.
    Records in database.
    """
    try:
        # Queue Celery task to record in DB
        celery.send_task(
            'tasks.record_screenshots_uploaded',
            kwargs={
                'screenshots': request.screenshots,
                'activity_type': request.activity_type,
                'session_id': request.session_id,
                'project_id': request.project_id,
                'company_id': request.company_id
            }
        )

        return {
            "success": True,
            "queued": True,
            "screenshots_count": len(request.screenshots)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm uploads: {str(e)}")


@router.post("/screenshots/confirm-zip")
async def confirm_screenshot_zip_upload(
        body: ScreenshotZipConfirmRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Confirm screenshot zip was uploaded to S3.
    Triggers Celery task to unzip and process.

    Used by: Celery method (docker-compose development)
    Not used by: Lambda method (AWS production) - Lambda triggered by S3 event
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != body.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Queue Celery task to process zip
        celery.send_task(
            'tasks.process_screenshot_zip',
            kwargs={
                's3_key': body.s3_key,
                'activity_type': body.activity_type,
                'session_id': body.session_id,
                'project_id': body.project_id,
                'company_id': body.company_id
            }
        )

        return {
            "success": True,
            "queued": True,
            "s3_key": body.s3_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm zip upload: {str(e)}")


@router.post("/form-files/confirm-zip")
async def confirm_form_files_zip_upload(
        body: FormFilesZipConfirmRequest,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Confirm form files zip was uploaded to S3.
    Triggers Celery task to unzip and process.

    Used by: Celery method (docker-compose development)
    Not used by: Lambda method (AWS production) - Lambda triggered by S3 event
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] != "super_admin" and current_user["company_id"] != body.company_id:
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        # Queue Celery task to process zip
        celery.send_task(
            'tasks.process_form_files_zip',
            kwargs={
                's3_key': body.s3_key,
                'activity_type': body.activity_type,
                'session_id': body.session_id,
                'project_id': body.project_id,
                'company_id': body.company_id,
                'form_page_route_id': body.form_page_route_id
            }
        )

        return {
            "success": True,
            "queued": True,
            "s3_key": body.s3_key
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm form files zip upload: {str(e)}")


# ============================================================================
# Screenshot Retrieval
# ============================================================================

@router.get("/sessions/{activity_type}/{session_id}/screenshots")
async def list_session_screenshots(
        activity_type: str,
        session_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    List all screenshots for a session.
    """
    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    screenshots = db.query(ActivityScreenshot).filter(
        ActivityScreenshot.activity_type == activity_type,
        ActivityScreenshot.session_id == session_id
    ).order_by(ActivityScreenshot.created_at).all()

    return {
        "session_id": session_id,
        "activity_type": activity_type,
        "screenshots": [
            ScreenshotInfo(
                id=s.id,
                filename=s.filename,
                s3_key=s.s3_key,
                file_size_bytes=s.file_size_bytes,
                created_at=s.created_at.isoformat() if s.created_at else ""
            ) for s in screenshots
        ],
        "total": len(screenshots)
    }


@router.get("/screenshots/{screenshot_id}/url")
async def get_screenshot_url(
        screenshot_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Get pre-signed URL to view/download a screenshot.
    """

    current_user = get_current_user_from_request(request)

    screenshot = db.query(ActivityScreenshot).filter(
        ActivityScreenshot.id == screenshot_id
    ).first()

    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != screenshot.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    url = get_screenshot_presigned_url(screenshot.s3_key, expiration=3600)

    return {
        "screenshot_id": screenshot_id,
        "filename": screenshot.filename,
        "url": url,
        "expires_in": 3600
    }


@router.get("/screenshots/by-filename")
async def get_screenshot_by_filename(
        activity_type: str,
        session_id: int,
        filename: str,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Get pre-signed URL for a screenshot by filename.
    Used by frontend to make [Screenshot: filename.png] clickable.
    """

    current_user = get_current_user_from_request(request)

    screenshot = db.query(ActivityScreenshot).filter(
        ActivityScreenshot.activity_type == activity_type,
        ActivityScreenshot.session_id == session_id,
        ActivityScreenshot.filename == filename
    ).first()

    if not screenshot:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    if current_user["type"] != "super_admin" and current_user["company_id"] != screenshot.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    url = get_screenshot_presigned_url(screenshot.s3_key, expiration=3600)

    return {
        "filename": filename,
        "url": url,
        "expires_in": 3600
    }

@router.get("/{activity_type}/{session_id}/screenshot-url")
async def get_session_screenshot_url(
        activity_type: str,
        session_id: int,
        request: Request,
        filename: str = Query(...),
        download: bool = Query(default=False),
        db: Session = Depends(get_db)
):
    """
    Get pre-signed URL for a screenshot.
    If download=true, returns URL with Content-Disposition: attachment header.
    """

    current_user = get_current_user_from_request(request)

    screenshot = db.query(ActivityScreenshot).filter(
        ActivityScreenshot.activity_type == activity_type,
        ActivityScreenshot.session_id == session_id,
        ActivityScreenshot.filename == filename
    ).first()

    if not screenshot:
        raise HTTPException(status_code=404, detail=f"Screenshot '{filename}' not found for session {session_id}")
    if current_user["type"] != "super_admin" and current_user["company_id"] != screenshot.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Generate URL with or without download disposition
    if download:
        url = get_screenshot_download_url(screenshot.s3_key, filename, expiration=3600)
    else:
        url = get_screenshot_presigned_url(screenshot.s3_key, expiration=3600)

    return {
        "filename": filename,
        "url": url,
        "expires_in": 3600
    }

# ============================================================================
# Download Endpoints
# ============================================================================

@router.get("/sessions/{activity_type}/{session_id}/screenshots/download")
async def download_session_screenshots(
        activity_type: str,
        session_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Download all screenshots for a session as a zip file.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    screenshots = db.query(ActivityScreenshot).filter(
        ActivityScreenshot.activity_type == activity_type,
        ActivityScreenshot.session_id == session_id,
        ActivityScreenshot.company_id == company_id
    ).all()

    if not screenshots:
        raise HTTPException(status_code=404, detail="No screenshots found")

    # Create zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for screenshot in screenshots:
            try:
                content = get_s3_file_content(screenshot.s3_key)
                zip_file.writestr(screenshot.filename, content)
            except Exception as e:
                # Skip failed downloads
                print(f"Failed to download {screenshot.s3_key}: {e}")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={activity_type}_{session_id}_screenshots.zip"
        }
    )


@router.get("/sessions/{activity_type}/{session_id}/logs/download")
async def download_session_logs(
        activity_type: str,
        session_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Download all logs for a session as JSON file.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    # Build filter
    if activity_type == "discovery":
        session_filter = ActivityLogEntry.crawl_session_id == session_id
    elif activity_type == "mapping":
        session_filter = ActivityLogEntry.mapper_session_id == session_id
    elif activity_type == "test_run":
        session_filter = ActivityLogEntry.test_run_id == session_id
    else:
        raise HTTPException(status_code=400, detail="Invalid activity type")

    entries = db.query(ActivityLogEntry).filter(session_filter).order_by(
        ActivityLogEntry.timestamp
    ).all()

    if not entries:
        raise HTTPException(status_code=404, detail="No logs found")

    # Convert to JSON
    logs_data = [
        {
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "level": e.level,
            "category": e.category,
            "message": e.message,
            "extra_data": e.extra_data
        } for e in entries
    ]

    json_content = json.dumps(logs_data, indent=2)

    return StreamingResponse(
        io.BytesIO(json_content.encode('utf-8')),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename={activity_type}_{session_id}_logs.json"
        }
    )


# ============================================================================
# GET Endpoints - Retrieve logs for frontend (unchanged)
# ============================================================================

@router.get("")
async def list_activity_sessions(
        project_id: int,
        request: Request,
        activity_type: Optional[str] = None,
        days: int = Query(default=7, le=90),
        has_errors: Optional[bool] = None,
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, le=100),
        db: Session = Depends(get_db)
):
    """
    List activity sessions for a project.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    sessions = []

    # Get discovery sessions
    if activity_type is None or activity_type == "discovery":
        discovery_query = db.query(CrawlSession).filter(
            CrawlSession.project_id == project_id,
            CrawlSession.created_at >= cutoff_date
        ).order_by(desc(CrawlSession.created_at))

        for cs in discovery_query.limit(limit).all():
            entry_count = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.crawl_session_id == cs.id
            ).count()

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

    # Get mapping sessions
    if activity_type is None or activity_type == "mapping":
        try:
            from models.database import FormPageRoute

            mapping_query = db.query(FormMapperSession, FormPageRoute.form_name).join(
                FormPageRoute, FormMapperSession.form_page_route_id == FormPageRoute.id
            ).filter(
                FormPageRoute.project_id == project_id,
                FormMapperSession.created_at >= cutoff_date
            ).order_by(desc(FormMapperSession.created_at))

            for ms, form_name in mapping_query.limit(limit).all():
                entry_count = db.query(ActivityLogEntry).filter(
                    ActivityLogEntry.mapper_session_id == ms.id
                ).count()

                error_count = db.query(ActivityLogEntry).filter(
                    ActivityLogEntry.mapper_session_id == ms.id,
                    ActivityLogEntry.level == 'error'
                ).count()

                if has_errors is not None:
                    if has_errors and error_count == 0:
                        continue
                    if not has_errors and error_count > 0:
                        continue

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
                    completed_at=ms.completed_at.isoformat() if hasattr(ms,
                                                                        'completed_at') and ms.completed_at else None,
                    entry_count=entry_count,
                    has_errors=error_count > 0,
                    summary=summary,
                    form_name=form_name
                ))
        except Exception as e:
            print(f"Warning: Could not load mapping sessions: {e}")

    sessions.sort(key=lambda x: x.started_at or "", reverse=True)

    offset = (page - 1) * limit
    paginated_sessions = sessions[offset:offset + limit]

    return ActivityLogsListResponse(
        sessions=paginated_sessions,
        total=len(sessions),
        page=page,
        page_size=limit
    )


@router.delete("/{activity_type}/{session_id}")
async def delete_session_logs(
        activity_type: str,
        session_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Delete all logs, screenshots, and the session record itself.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    try:
        # Delete log entries
        if activity_type == "discovery":
            deleted_logs = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.crawl_session_id == session_id
            ).delete()
            # Delete the crawl session itself
            db.query(CrawlSession).filter(CrawlSession.id == session_id).delete()

        elif activity_type == "mapping":
            deleted_logs = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.mapper_session_id == session_id
            ).delete()
            # Delete the mapper session itself
            db.query(FormMapperSession).filter(FormMapperSession.id == session_id).delete()

        elif activity_type == "test_run":
            deleted_logs = db.query(ActivityLogEntry).filter(
                ActivityLogEntry.test_run_id == session_id
            ).delete()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown activity type: {activity_type}")

        # Get screenshots for S3 cleanup
        screenshots = db.query(ActivityScreenshot).filter(
            ActivityScreenshot.activity_type == activity_type,
            ActivityScreenshot.session_id == session_id
        ).all()

        screenshot_count = len(screenshots)

        # Delete screenshot records and queue S3 cleanup
        if screenshots:
            s3_keys = [s.s3_key for s in screenshots]
            celery.send_task(
                'tasks.delete_s3_files',
                kwargs={'s3_keys': s3_keys}
            )

            db.query(ActivityScreenshot).filter(
                ActivityScreenshot.activity_type == activity_type,
                ActivityScreenshot.session_id == session_id
            ).delete()

        db.commit()

        return {
            "success": True,
            "deleted_logs": deleted_logs,
            "deleted_screenshots": screenshot_count,
            "activity_type": activity_type,
            "session_id": session_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete session logs: {str(e)}")


@router.get("/{session_type}/{session_id}")
async def get_session_logs(
        session_type: str,
        session_id: int,
        request: Request,
        level: Optional[str] = None,
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=100, le=500),
        db: Session = Depends(get_db)
):
    """
    Get log entries for a specific session.
    """

    current_user = get_current_user_from_request(request)
    company_id = current_user["company_id"]

    if session_type == "discovery":
        session_filter = ActivityLogEntry.crawl_session_id == session_id
        session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        status = session.status
        started_at = session.started_at.isoformat() if session.started_at else None
        completed_at = session.completed_at.isoformat() if session.completed_at else None
    elif session_type == "mapping":
        session_filter = ActivityLogEntry.mapper_session_id == session_id
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

    query = db.query(ActivityLogEntry).filter(session_filter)

    if level:
        query = query.filter(ActivityLogEntry.level == level)

    total = query.count()

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