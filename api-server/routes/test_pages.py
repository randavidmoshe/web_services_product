# ============================================================================
# Test Pages - API Endpoints (Dynamic Content Testing)
# ============================================================================
# FastAPI router for Test Page endpoints:
# - POST /test-pages - Create test page
# - GET /test-pages - List test pages for project
# - GET /test-pages/{id} - Get test page
# - PUT /test-pages/{id} - Update test page
# - DELETE /test-pages/{id} - Delete test page
# - POST /test-pages/{id}/start-mapping - Start mapping
# - GET /test-pages/{id}/paths - Get completed paths
# ============================================================================

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, Network
from models.test_page_models import TestPageRoute
from models.form_mapper_models import FormMapperSession, FormMapResult
from services.form_mapper_orchestrator import FormMapperOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test-pages", tags=["Test Pages"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateTestPageRequest(BaseModel):
    """Request to create a test page"""
    project_id: int
    company_id: int
    network_id: int
    url: str
    test_name: str
    test_case_description: str
    created_by: Optional[int] = None


class UpdateTestPageRequest(BaseModel):
    """Request to update a test page"""
    url: Optional[str] = None
    test_name: Optional[str] = None
    test_case_description: Optional[str] = None
    network_id: Optional[int] = None


class TestPageResponse(BaseModel):
    """Test page response"""
    id: int
    project_id: int
    company_id: int
    network_id: int
    url: str
    test_name: str
    test_case_description: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TestPageListResponse(BaseModel):
    """List of test pages"""
    total: int
    test_pages: List[TestPageResponse]


class StartMappingRequest(BaseModel):
    """Request to start dynamic content mapping"""
    user_id: int
    agent_id: Optional[str] = None
    config: Optional[dict] = None


class StartMappingResponse(BaseModel):
    """Response after starting mapping"""
    session_id: str
    status: str
    message: str


class CompletedPathResponse(BaseModel):
    """A completed mapping path"""
    id: int
    path_number: int
    steps: List[dict]
    steps_count: int
    created_at: Optional[str] = None


class CompletedPathsListResponse(BaseModel):
    """List of completed paths"""
    test_page_route_id: int
    total_paths: int
    paths: List[CompletedPathResponse]


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.post("", response_model=TestPageResponse, status_code=201)
async def create_test_page(
        request: CreateTestPageRequest,
        db: Session = Depends(get_db)
):
    """Create a new test page for dynamic content testing"""

    # Validate network exists
    network = db.query(Network).filter(Network.id == request.network_id).first()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")

    # Create test page
    test_page = TestPageRoute(
        project_id=request.project_id,
        company_id=request.company_id,
        network_id=request.network_id,
        url=request.url,
        test_name=request.test_name,
        test_case_description=request.test_case_description,
        status="not_mapped",
        created_by=request.created_by
    )

    db.add(test_page)
    db.commit()
    db.refresh(test_page)

    logger.info(f"[API] Created test page {test_page.id}: {test_page.test_name}")

    return TestPageResponse(
        id=test_page.id,
        project_id=test_page.project_id,
        company_id=test_page.company_id,
        network_id=test_page.network_id,
        url=test_page.url,
        test_name=test_page.test_name,
        test_case_description=test_page.test_case_description,
        status=test_page.status,
        created_at=test_page.created_at.isoformat() if test_page.created_at else None,
        updated_at=test_page.updated_at.isoformat() if test_page.updated_at else None
    )


@router.get("", response_model=TestPageListResponse)
async def list_test_pages(
        project_id: int,
        db: Session = Depends(get_db)
):
    """List all test pages for a project"""

    test_pages = db.query(TestPageRoute).filter(
        TestPageRoute.project_id == project_id
    ).order_by(TestPageRoute.created_at.desc()).all()

    return TestPageListResponse(
        total=len(test_pages),
        test_pages=[
            TestPageResponse(
                id=tp.id,
                project_id=tp.project_id,
                company_id=tp.company_id,
                network_id=tp.network_id,
                url=tp.url,
                test_name=tp.test_name,
                test_case_description=tp.test_case_description,
                status=tp.status,
                created_at=tp.created_at.isoformat() if tp.created_at else None,
                updated_at=tp.updated_at.isoformat() if tp.updated_at else None
            )
            for tp in test_pages
        ]
    )


@router.get("/{test_page_id}", response_model=TestPageResponse)
async def get_test_page(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Get a test page by ID"""

    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    return TestPageResponse(
        id=test_page.id,
        project_id=test_page.project_id,
        company_id=test_page.company_id,
        network_id=test_page.network_id,
        url=test_page.url,
        test_name=test_page.test_name,
        test_case_description=test_page.test_case_description,
        status=test_page.status,
        created_at=test_page.created_at.isoformat() if test_page.created_at else None,
        updated_at=test_page.updated_at.isoformat() if test_page.updated_at else None
    )


@router.put("/{test_page_id}", response_model=TestPageResponse)
async def update_test_page(
        test_page_id: int,
        request: UpdateTestPageRequest,
        db: Session = Depends(get_db)
):
    """Update a test page"""

    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    if request.url is not None:
        test_page.url = request.url
    if request.test_name is not None:
        test_page.test_name = request.test_name
    if request.test_case_description is not None:
        test_page.test_case_description = request.test_case_description
    if request.network_id is not None:
        test_page.network_id = request.network_id

    db.commit()
    db.refresh(test_page)

    logger.info(f"[API] Updated test page {test_page.id}")

    return TestPageResponse(
        id=test_page.id,
        project_id=test_page.project_id,
        company_id=test_page.company_id,
        network_id=test_page.network_id,
        url=test_page.url,
        test_name=test_page.test_name,
        test_case_description=test_page.test_case_description,
        status=test_page.status,
        created_at=test_page.created_at.isoformat() if test_page.created_at else None,
        updated_at=test_page.updated_at.isoformat() if test_page.updated_at else None
    )


@router.delete("/{test_page_id}")
async def delete_test_page(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Delete a test page"""

    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    db.delete(test_page)
    db.commit()

    logger.info(f"[API] Deleted test page {test_page_id}")

    return {"success": True, "message": "Test page deleted"}


# ============================================================================
# Mapping Endpoints
# ============================================================================

@router.post("/{test_page_id}/start-mapping", response_model=StartMappingResponse, status_code=202)
async def start_test_page_mapping(
        test_page_id: int,
        request: StartMappingRequest,
        db: Session = Depends(get_db)
):
    """Start mapping a test page (dynamic content)"""

    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    # Get network for login
    network = db.query(Network).filter(Network.id == test_page.network_id).first()
    if not network:
        raise HTTPException(status_code=400, detail="Network not found for test page")

    agent_id = request.agent_id or f"agent-{request.user_id}"

    # Create DB session
    db_session = FormMapperSession(
        test_page_route_id=test_page_id,
        form_page_route_id=None,
        user_id=request.user_id,
        network_id=test_page.network_id,
        company_id=test_page.company_id,
        agent_id=agent_id,
        status="initializing",
        config=request.config or {}
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Create orchestrator session
    orchestrator = FormMapperOrchestrator(db)
    orchestrator.create_session(
        session_id=str(db_session.id),
        user_id=request.user_id,
        company_id=test_page.company_id,
        network_id=test_page.network_id,
        test_page_route_id=test_page_id,
        mapping_type="dynamic_content",
        test_case_description=test_page.test_case_description,
        config=request.config,
        test_cases=[]  # Dynamic content uses test_case_description instead
    )

    # Start login phase
    result = orchestrator.start_login_phase(session_id=str(db_session.id))

    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Failed to start mapping")

    # Update test page status
    test_page.status = "mapping"
    db.commit()

    logger.info(f"[API] Started dynamic content mapping session {db_session.id} for test page {test_page_id}")

    return StartMappingResponse(
        session_id=str(db_session.id),
        status="started",
        message=f"Mapping started for test page: {test_page.test_name}"
    )


@router.get("/{test_page_id}/paths", response_model=CompletedPathsListResponse)
async def get_test_page_paths(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Get completed mapping paths for a test page"""

    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    paths = db.query(FormMapResult).filter(
        FormMapResult.test_page_route_id == test_page_id
    ).order_by(FormMapResult.path_number.asc()).all()

    return CompletedPathsListResponse(
        test_page_route_id=test_page_id,
        total_paths=len(paths),
        paths=[
            CompletedPathResponse(
                id=p.id,
                path_number=p.path_number,
                steps=p.steps or [],
                steps_count=len(p.steps) if p.steps else 0,
                created_at=p.created_at.isoformat() if p.created_at else None
            )
            for p in paths
        ]
    )