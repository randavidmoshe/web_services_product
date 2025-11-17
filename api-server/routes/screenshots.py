from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from models.database import get_db, Screenshot
from services.s3_storage import upload_screenshot_to_s3, delete_screenshot_from_s3, get_screenshot_presigned_url
from typing import Optional

router = APIRouter()

@router.post("/upload")
async def upload_screenshot(
    image: UploadFile = File(...),
    company_id: int = Form(...),
    crawl_session_id: int = Form(...),
    image_type: str = Form(...),
    form_page_id: Optional[int] = Form(None),
    product_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a screenshot to S3 and save metadata to database
    
    Args:
        image: Image file (PNG/JPG)
        company_id: Company ID
        crawl_session_id: Crawl session ID
        image_type: Type of screenshot (initial_load, after_interaction, error, etc)
        form_page_id: Optional form page ID
        product_id: Optional product ID
        description: Optional description
        user_id: Optional user ID who uploaded
    
    Returns:
        Screenshot metadata with S3 URL
    """
    
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(400, "File must be an image")
        
        # Upload to S3
        s3_metadata = upload_screenshot_to_s3(
            image_bytes=image_bytes,
            company_id=company_id,
            session_id=crawl_session_id,
            filename=image.filename,
            image_type=image_type
        )
        
        # Save to database
        screenshot = Screenshot(
            company_id=company_id,
            product_id=product_id,
            crawl_session_id=crawl_session_id,
            form_page_id=form_page_id,
            filename=image.filename,
            image_type=image_type,
            description=description,
            s3_bucket=s3_metadata['s3_bucket'],
            s3_key=s3_metadata['s3_key'],
            s3_url=s3_metadata['s3_url'],
            file_size_bytes=s3_metadata['file_size_bytes'],
            width_px=s3_metadata.get('width_px'),
            height_px=s3_metadata.get('height_px'),
            content_type=image.content_type,
            uploaded_by_user_id=user_id
        )
        
        db.add(screenshot)
        db.commit()
        db.refresh(screenshot)
        
        return {
            "id": screenshot.id,
            "url": screenshot.s3_url,
            "s3_key": screenshot.s3_key,
            "filename": screenshot.filename,
            "image_type": screenshot.image_type,
            "file_size_bytes": screenshot.file_size_bytes,
            "width_px": screenshot.width_px,
            "height_px": screenshot.height_px,
            "created_at": screenshot.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error uploading screenshot: {str(e)}")


@router.get("/session/{session_id}")
async def get_session_screenshots(
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all screenshots for a crawl session
    """
    screenshots = db.query(Screenshot).filter(
        Screenshot.crawl_session_id == session_id
    ).order_by(Screenshot.created_at.desc()).all()
    
    return [{
        "id": s.id,
        "url": s.s3_url,
        "filename": s.filename,
        "image_type": s.image_type,
        "description": s.description,
        "file_size_bytes": s.file_size_bytes,
        "width_px": s.width_px,
        "height_px": s.height_px,
        "created_at": s.created_at
    } for s in screenshots]


@router.get("/form-page/{form_page_id}")
async def get_form_page_screenshots(
    form_page_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all screenshots for a specific form page
    """
    screenshots = db.query(Screenshot).filter(
        Screenshot.form_page_id == form_page_id
    ).order_by(Screenshot.created_at.desc()).all()
    
    return [{
        "id": s.id,
        "url": s.s3_url,
        "filename": s.filename,
        "image_type": s.image_type,
        "description": s.description,
        "created_at": s.created_at
    } for s in screenshots]


@router.get("/{screenshot_id}")
async def get_screenshot(
    screenshot_id: int,
    db: Session = Depends(get_db)
):
    """
    Get screenshot metadata by ID
    """
    screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    
    if not screenshot:
        raise HTTPException(404, "Screenshot not found")
    
    return {
        "id": screenshot.id,
        "url": screenshot.s3_url,
        "filename": screenshot.filename,
        "image_type": screenshot.image_type,
        "description": screenshot.description,
        "file_size_bytes": screenshot.file_size_bytes,
        "width_px": screenshot.width_px,
        "height_px": screenshot.height_px,
        "created_at": screenshot.created_at,
        "company_id": screenshot.company_id,
        "crawl_session_id": screenshot.crawl_session_id,
        "form_page_id": screenshot.form_page_id
    }


@router.get("/{screenshot_id}/presigned-url")
async def get_screenshot_presigned(
    screenshot_id: int,
    expiration: int = 3600,
    db: Session = Depends(get_db)
):
    """
    Get presigned URL for private screenshot access
    """
    screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    
    if not screenshot:
        raise HTTPException(404, "Screenshot not found")
    
    try:
        presigned_url = get_screenshot_presigned_url(screenshot.s3_key, expiration)
        return {"url": presigned_url, "expires_in": expiration}
    except Exception as e:
        raise HTTPException(500, f"Error generating presigned URL: {str(e)}")


@router.delete("/{screenshot_id}")
async def delete_screenshot(
    screenshot_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete screenshot from S3 and database
    """
    screenshot = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    
    if not screenshot:
        raise HTTPException(404, "Screenshot not found")
    
    try:
        # Delete from S3
        delete_screenshot_from_s3(screenshot.s3_key)
        
        # Delete from database
        db.delete(screenshot)
        db.commit()
        
        return {"message": "Screenshot deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Error deleting screenshot: {str(e)}")
