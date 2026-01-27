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
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db, Network
from models.test_page_models import TestPageRoute, TestPageReferenceImage
from models.form_mapper_models import FormMapperSession, FormMapResult
from services.form_mapper_orchestrator import FormMapperOrchestrator
from services.s3_storage import generate_presigned_put_url, get_screenshot_presigned_url, delete_screenshot_from_s3, S3_BUCKET
from services.test_page_visual_assets import validate_image_upload, validate_file_upload, MAX_IMAGES_PER_TEST_PAGE
from sqlalchemy.orm.attributes import flag_modified
from celery_app import celery

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

# ============================================================================
# Visual Assets - Request/Response Models
# ============================================================================

class RequestUploadResponse(BaseModel):
    """Response with presigned URL for direct S3 upload"""
    id: Optional[int] = None
    presigned_url: str
    s3_key: str
    s3_bucket: str
    expires_in: int = 900


class ReferenceImageResponse(BaseModel):
    """Reference image details"""
    id: int
    name: str
    description: Optional[str] = None
    filename: str
    status: str
    file_size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    presigned_url: Optional[str] = None
    created_at: Optional[str] = None


class ReferenceImagesListResponse(BaseModel):
    """List of reference images"""
    test_page_route_id: int
    total: int
    max_allowed: int
    images: List[ReferenceImageResponse]


class ConfirmUploadRequest(BaseModel):
    """Confirm upload completed"""
    file_size_bytes: Optional[int] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None


class UpdateReferenceImageRequest(BaseModel):
    """Update reference image metadata"""
    name: Optional[str] = None
    description: Optional[str] = None


class VerificationFileResponse(BaseModel):
    """Verification file details"""
    filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: Optional[str] = None
    presigned_url: Optional[str] = None
    content_preview: Optional[str] = None
    uploaded_at: Optional[str] = None


class RequestVerificationFileUploadRequest(BaseModel):
    """Request to upload verification file"""
    filename: str
    content_type: str
    file_size_bytes: Optional[int] = None

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

    # Cleanup previous sessions and results (async via Celery)
    celery.send_task(
        'tasks.cancel_previous_sessions_for_test_page',
        kwargs={
            'test_page_route_id': test_page_id,
            'new_session_id': db_session.id  # Will be updated after session creation
        }
    )
    logger.info(f"[API] Queued cleanup for test page {test_page_id}")

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


# ============================================================================
# Visual Assets - Reference Images Endpoints
# ============================================================================

@router.post("/{test_page_id}/reference-images/request-upload", response_model=RequestUploadResponse)
async def request_reference_image_upload(
        test_page_id: int,
        name: str = Query(..., description="Image name"),
        filename: str = Query(..., description="Original filename"),
        content_type: str = Query(..., description="MIME type"),
        file_size_bytes: int = Query(..., description="File size in bytes"),
        description: str = Query(None, description="Optional description"),
        db: Session = Depends(get_db)
):
    """Request presigned URL for reference image upload"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    current_count = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.test_page_route_id == test_page_id
    ).count()

    if current_count >= MAX_IMAGES_PER_TEST_PAGE:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES_PER_TEST_PAGE} reference images allowed")

    is_valid, error = validate_image_upload(content_type, file_size_bytes)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    ref_image = TestPageReferenceImage(
        test_page_route_id=test_page_id,
        company_id=test_page.company_id,
        name=name,
        description=description,
        status="pending",
        s3_key="pending",
        s3_bucket=S3_BUCKET,
        filename=filename,
        file_size_bytes=file_size_bytes,
        content_type=content_type
    )
    db.add(ref_image)
    db.commit()
    db.refresh(ref_image)

    s3_key = f"reference_images/{test_page.company_id}/{test_page.project_id}/test_page_{test_page_id}/{ref_image.id}_{filename}"
    ref_image.s3_key = s3_key
    db.commit()

    presigned_url = generate_presigned_put_url(s3_key, content_type)

    logger.info(f"[API] Generated presigned URL for reference image {ref_image.id}")

    return RequestUploadResponse(
        id=ref_image.id,
        presigned_url=presigned_url,
        s3_key=s3_key,
        s3_bucket=S3_BUCKET,
        expires_in=900
    )


@router.post("/{test_page_id}/reference-images/{image_id}/confirm-upload", response_model=ReferenceImageResponse)
async def confirm_reference_image_upload(
        test_page_id: int,
        image_id: int,
        request: ConfirmUploadRequest,
        db: Session = Depends(get_db)
):
    """Confirm reference image upload completed"""
    image = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.id == image_id,
        TestPageReferenceImage.test_page_route_id == test_page_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Reference image not found")

    if image.status == "ready":
        raise HTTPException(status_code=400, detail="Upload already confirmed")

    image.status = "ready"
    if request.file_size_bytes:
        image.file_size_bytes = request.file_size_bytes
    if request.width_px:
        image.width_px = request.width_px
    if request.height_px:
        image.height_px = request.height_px

    db.commit()
    db.refresh(image)

    logger.info(f"[API] Confirmed reference image upload {image_id}")

    return ReferenceImageResponse(
        id=image.id,
        name=image.name,
        description=image.description,
        filename=image.filename,
        status=image.status,
        file_size_bytes=image.file_size_bytes,
        content_type=image.content_type,
        width_px=image.width_px,
        height_px=image.height_px,
        presigned_url=None,
        created_at=image.created_at.isoformat() if image.created_at else None
    )


@router.get("/{test_page_id}/reference-images", response_model=ReferenceImagesListResponse)
async def list_reference_images(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """List all reference images for a test page"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    images = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.test_page_route_id == test_page_id,
        TestPageReferenceImage.status == "ready"
    ).order_by(TestPageReferenceImage.created_at.asc()).all()

    return ReferenceImagesListResponse(
        test_page_route_id=test_page_id,
        total=len(images),
        max_allowed=MAX_IMAGES_PER_TEST_PAGE,
        images=[
            ReferenceImageResponse(
                id=img.id,
                name=img.name,
                description=img.description,
                filename=img.filename,
                status=img.status,
                file_size_bytes=img.file_size_bytes,
                content_type=img.content_type,
                width_px=img.width_px,
                height_px=img.height_px,
                presigned_url=None,
                created_at=img.created_at.isoformat() if img.created_at else None
            )
            for img in images
        ]
    )


@router.get("/{test_page_id}/reference-images/{image_id}", response_model=ReferenceImageResponse)
async def get_reference_image(
        test_page_id: int,
        image_id: int,
        db: Session = Depends(get_db)
):
    """Get reference image with presigned URL for viewing"""
    image = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.id == image_id,
        TestPageReferenceImage.test_page_route_id == test_page_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Reference image not found")

    presigned_url = get_screenshot_presigned_url(image.s3_key) if image.status == "ready" else None

    return ReferenceImageResponse(
        id=image.id,
        name=image.name,
        description=image.description,
        filename=image.filename,
        status=image.status,
        file_size_bytes=image.file_size_bytes,
        content_type=image.content_type,
        width_px=image.width_px,
        height_px=image.height_px,
        presigned_url=presigned_url,
        created_at=image.created_at.isoformat() if image.created_at else None
    )


@router.put("/{test_page_id}/reference-images/{image_id}", response_model=ReferenceImageResponse)
async def update_reference_image(
        test_page_id: int,
        image_id: int,
        request: UpdateReferenceImageRequest,
        db: Session = Depends(get_db)
):
    """Update reference image name/description"""
    image = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.id == image_id,
        TestPageReferenceImage.test_page_route_id == test_page_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Reference image not found")

    if request.name is not None:
        image.name = request.name
    if request.description is not None:
        image.description = request.description

    db.commit()
    db.refresh(image)

    return ReferenceImageResponse(
        id=image.id,
        name=image.name,
        description=image.description,
        filename=image.filename,
        status=image.status,
        file_size_bytes=image.file_size_bytes,
        content_type=image.content_type,
        width_px=image.width_px,
        height_px=image.height_px,
        presigned_url=None,
        created_at=image.created_at.isoformat() if image.created_at else None
    )


@router.delete("/{test_page_id}/reference-images/{image_id}")
async def delete_reference_image(
        test_page_id: int,
        image_id: int,
        db: Session = Depends(get_db)
):
    """Delete reference image"""
    image = db.query(TestPageReferenceImage).filter(
        TestPageReferenceImage.id == image_id,
        TestPageReferenceImage.test_page_route_id == test_page_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Reference image not found")

    if image.s3_key and image.s3_key != "pending":
        celery.send_task('tasks.delete_s3_file', kwargs={'s3_key': image.s3_key})

    db.delete(image)
    db.commit()

    return {"success": True, "message": "Reference image deleted"}


# ============================================================================
# Visual Assets - Verification File Endpoints
# ============================================================================

@router.post("/{test_page_id}/verification-file/request-upload", response_model=RequestUploadResponse)
async def request_verification_file_upload(
        test_page_id: int,
        request: RequestVerificationFileUploadRequest,
        db: Session = Depends(get_db)
):
    """Request presigned URL for verification file upload"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    is_valid, error = validate_file_upload(request.content_type, request.file_size_bytes or 0, request.filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    if test_page.verification_file and test_page.verification_file.get('s3_key'):
        celery.send_task('tasks.delete_s3_file', kwargs={'s3_key': test_page.verification_file['s3_key']})

    s3_key = f"verification_files/{test_page.company_id}/{test_page.project_id}/test_page_{test_page_id}/{request.filename}"

    test_page.verification_file = {
        "filename": request.filename,
        "s3_key": s3_key,
        "s3_bucket": S3_BUCKET,
        "content_type": request.content_type,
        "file_size_bytes": request.file_size_bytes,
        "status": "pending",
        "uploaded_at": None
    }
    test_page.verification_file_content = None
    flag_modified(test_page, "verification_file")
    db.commit()

    presigned_url = generate_presigned_put_url(s3_key, request.content_type)

    logger.info(f"[API] Generated presigned URL for verification file, test page {test_page_id}")

    return RequestUploadResponse(
        presigned_url=presigned_url,
        s3_key=s3_key,
        s3_bucket=S3_BUCKET,
        expires_in=900
    )


@router.post("/{test_page_id}/verification-file/confirm-upload")
async def confirm_verification_file_upload(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Confirm verification file upload - triggers text extraction via Celery"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    if not test_page.verification_file:
        raise HTTPException(status_code=400, detail="No verification file upload in progress")

    if test_page.verification_file.get('status') == 'ready':
        raise HTTPException(status_code=400, detail="Upload already confirmed")

    test_page.verification_file['status'] = 'processing'
    test_page.verification_file['uploaded_at'] = datetime.utcnow().isoformat()
    flag_modified(test_page, "verification_file")
    db.commit()

    celery.send_task(
        'tasks.extract_verification_file_text',
        kwargs={
            'test_page_id': test_page_id,
            's3_key': test_page.verification_file['s3_key'],
            'content_type': test_page.verification_file['content_type'],
            'filename': test_page.verification_file['filename']
        }
    )

    logger.info(f"[API] Queued text extraction for verification file, test page {test_page_id}")

    return {"success": True, "status": "processing", "message": "Text extraction queued"}


@router.get("/{test_page_id}/verification-file")
async def get_verification_file(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Get verification file info and content"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    if not test_page.verification_file:
        return {"verification_file": None}

    vf = test_page.verification_file
    presigned_url = get_screenshot_presigned_url(vf['s3_key']) if vf.get('s3_key') and vf.get('status') == 'ready' else None

    return {
        "verification_file": VerificationFileResponse(
            filename=vf.get('filename'),
            content_type=vf.get('content_type'),
            file_size_bytes=vf.get('file_size_bytes'),
            status=vf.get('status'),
            presigned_url=presigned_url,
            content_preview=test_page.verification_file_content[:500] if test_page.verification_file_content else None,
            uploaded_at=vf.get('uploaded_at')
        ),
        "content": test_page.verification_file_content
    }


@router.delete("/{test_page_id}/verification-file")
async def delete_verification_file(
        test_page_id: int,
        db: Session = Depends(get_db)
):
    """Delete verification file"""
    test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
    if not test_page:
        raise HTTPException(status_code=404, detail="Test page not found")

    if not test_page.verification_file:
        raise HTTPException(status_code=404, detail="No verification file exists")

    if test_page.verification_file.get('s3_key'):
        celery.send_task('tasks.delete_s3_file', kwargs={'s3_key': test_page.verification_file['s3_key']})

    test_page.verification_file = None
    test_page.verification_file_content = None
    db.commit()

    return {"success": True, "message": "Verification file deleted"}