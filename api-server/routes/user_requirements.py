# ============================================================================
# User Requirements API Routes
# ============================================================================

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, FormPageRoute

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/form-mapper/form-pages", tags=["User Requirements"])


class UserProvidedInputsResponse(BaseModel):
    form_page_route_id: int
    status: str  # "parsing", "ready", "error", or "none"
    inputs: Optional[dict] = None
    raw_content: Optional[str] = None
    error: Optional[str] = None


@router.post("/{form_page_route_id}/user-inputs")
async def upload_user_inputs(
        form_page_route_id: int,
        file: Optional[UploadFile] = File(None),
        content: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """
    Upload user-provided inputs file.
    Returns immediately, parsing happens async.
    Poll GET endpoint for result.
    """
    form_page = db.query(FormPageRoute).filter(
        FormPageRoute.id == form_page_route_id
    ).first()

    if not form_page:
        raise HTTPException(status_code=404, detail="Form page route not found")

    raw_content = ""
    file_type = "txt"

    if file:
        file_content = await file.read()
        raw_content = file_content.decode('utf-8', errors='ignore')

        filename = file.filename.lower() if file.filename else ""
        if filename.endswith('.json'):
            file_type = "json"
        elif filename.endswith('.csv'):
            file_type = "csv"
        else:
            file_type = "txt"
    elif content:
        raw_content = content
    else:
        raise HTTPException(status_code=400, detail="No file or content provided")

    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="Empty content provided")

    try:
        # Save raw content and set status to parsing
        form_page.user_provided_inputs_raw = raw_content
        form_page.user_provided_inputs = {"status": "parsing"}
        db.commit()

        # Fire Celery task (no wait)
        from celery_app import celery  # Ensure celery app is loaded first
        from tasks.user_requirements_tasks import parse_user_inputs
        parse_user_inputs.delay(
            form_page_route_id=form_page_route_id,
            content=raw_content,
            file_type=file_type,
            company_id=form_page.company_id,
            product_id=form_page.product_id or 1,
            user_id=None
        )

        logger.info(f"[UserInputs] Started parsing for form page {form_page_route_id}")

        return {
            "success": True,
            "form_page_route_id": form_page_route_id,
            "status": "parsing",
            "message": "Parsing started. Poll GET endpoint for result."
        }

    except Exception as e:
        logger.error(f"[UserInputs] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{form_page_route_id}/user-inputs", response_model=UserProvidedInputsResponse)
async def get_user_inputs(
        form_page_route_id: int,
        db: Session = Depends(get_db)
):
    """
    Get current user-provided inputs for a form page.
    Poll this endpoint after POST to check parsing status.
    """
    form_page = db.query(FormPageRoute).filter(
        FormPageRoute.id == form_page_route_id
    ).first()

    if not form_page:
        raise HTTPException(status_code=404, detail="Form page route not found")

    inputs = form_page.user_provided_inputs

    if inputs is None:
        return UserProvidedInputsResponse(
            form_page_route_id=form_page_route_id,
            status="none",
            inputs=None,
            raw_content=form_page.user_provided_inputs_raw
        )

    status = inputs.get("status", "ready")

    if status == "error":
        return UserProvidedInputsResponse(
            form_page_route_id=form_page_route_id,
            status="error",
            inputs=None,
            raw_content=form_page.user_provided_inputs_raw,
            error=inputs.get("error")
        )

    if status == "parsing":
        return UserProvidedInputsResponse(
            form_page_route_id=form_page_route_id,
            status="parsing",
            inputs=None,
            raw_content=form_page.user_provided_inputs_raw
        )

    # status == "ready"
    return UserProvidedInputsResponse(
        form_page_route_id=form_page_route_id,
        status="ready",
        inputs=inputs,
        raw_content=form_page.user_provided_inputs_raw
    )


@router.delete("/{form_page_route_id}/user-inputs")
async def delete_user_inputs(
        form_page_route_id: int,
        db: Session = Depends(get_db)
):
    """Clear user-provided inputs for a form page."""
    form_page = db.query(FormPageRoute).filter(
        FormPageRoute.id == form_page_route_id
    ).first()

    if not form_page:
        raise HTTPException(status_code=404, detail="Form page route not found")

    form_page.user_provided_inputs = None
    form_page.user_provided_inputs_raw = None
    db.commit()

    logger.info(f"[UserInputs] Cleared inputs for form page {form_page_route_id}")

    return {
        "success": True,
        "form_page_route_id": form_page_route_id,
        "message": "User inputs cleared"
    }