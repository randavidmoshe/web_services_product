"""
Test Templates API Routes
Provides endpoints to list and get test templates for form mapping
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from utils.auth_helpers import get_current_user_from_request
from typing import List
from pydantic import BaseModel
from models.database import get_db, TestTemplate
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test-templates", tags=["test-templates"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TestCaseItem(BaseModel):
    test_id: str
    description: str
    expected_outcome: str


class TestTemplateResponse(BaseModel):
    id: int
    name: str
    display_name: str
    test_cases: List[dict]
    is_active: bool

    class Config:
        from_attributes = True


class TestTemplateListResponse(BaseModel):
    templates: List[TestTemplateResponse]


# ============================================================================
# ROUTES
# ============================================================================

@router.get("", response_model=TestTemplateListResponse)
async def list_test_templates(
        request: Request,
        active_only: bool = True,
        db: Session = Depends(get_db)
):
    """
    Get all available test templates
    """
    get_current_user_from_request(request)  # Verify authenticated
    try:
        query = db.query(TestTemplate)
        if active_only:
            query = query.filter(TestTemplate.is_active == True)

        templates = query.all()

        return TestTemplateListResponse(
            templates=[
                TestTemplateResponse(
                    id=t.id,
                    name=t.name,
                    display_name=t.display_name,
                    test_cases=t.test_cases,
                    is_active=t.is_active
                )
                for t in templates
            ]
        )
    except Exception as e:
        logger.error(f"Error listing test templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}", response_model=TestTemplateResponse)
async def get_test_template(
        template_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    """
    Get a specific test template by ID
    """
    get_current_user_from_request(request)  # Verify authenticated
    try:
        template = db.query(TestTemplate).filter(TestTemplate.id == template_id).first()

        if not template:
            raise HTTPException(status_code=404, detail="Test template not found")

        return TestTemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            test_cases=template.test_cases,
            is_active=template.is_active
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))