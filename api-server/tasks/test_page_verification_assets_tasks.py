# tasks/test_page_verification_assets_tasks.py
# Celery tasks for visual assets: S3 deletion, text extraction

import logging
from celery_app import celery
from models.database import SessionLocal
from models.test_page_models import TestPageRoute
from services.s3_storage import delete_screenshot_from_s3, get_s3_file_content
from services.test_page_visual_assets import extract_text_from_file
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)


@celery.task(name='tasks.delete_s3_file')
def delete_s3_file(s3_key: str):
    """Delete a file from S3"""
    try:
        result = delete_screenshot_from_s3(s3_key)
        logger.info(f"[Celery] Deleted S3 file: {s3_key}, success={result}")
        return {"success": result, "s3_key": s3_key}
    except Exception as e:
        logger.error(f"[Celery] Failed to delete S3 file {s3_key}: {e}")
        return {"success": False, "error": str(e)}


@celery.task(name='tasks.extract_verification_file_text')
def extract_verification_file_text(
        test_page_id: int,
        s3_key: str,
        content_type: str,
        filename: str
):
    """Download verification file from S3 and extract text"""
    db = SessionLocal()
    try:
        test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
        if not test_page:
            logger.error(f"[Celery] Test page {test_page_id} not found")
            return {"success": False, "error": "Test page not found"}

        # Download file from S3
        file_bytes = get_s3_file_content(s3_key)

        # Extract text
        extracted_text = extract_text_from_file(file_bytes, content_type, filename)

        # Update DB
        test_page.verification_file['status'] = 'ready'
        test_page.verification_file_content = extracted_text
        flag_modified(test_page, "verification_file")
        db.commit()

        logger.info(
            f"[Celery] Extracted text for test page {test_page_id}, {len(extracted_text) if extracted_text else 0} chars")
        return {"success": True, "test_page_id": test_page_id,
                "text_length": len(extracted_text) if extracted_text else 0}

    except Exception as e:
        logger.error(f"[Celery] Failed to extract text for test page {test_page_id}: {e}")
        # Mark as failed
        try:
            if test_page and test_page.verification_file:
                test_page.verification_file['status'] = 'failed'
                flag_modified(test_page, "verification_file")
                db.commit()
        except:
            pass
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery.task(name='tasks.cleanup_test_page_s3_files')
def cleanup_test_page_s3_files(test_page_id: int):
    """Cleanup all S3 files for a test page (called on delete)"""
    db = SessionLocal()
    try:
        from models.test_page_models import TestPageReferenceImage

        # Get all reference images
        images = db.query(TestPageReferenceImage).filter(
            TestPageReferenceImage.test_page_route_id == test_page_id
        ).all()

        deleted_count = 0
        for img in images:
            if img.s3_key and img.s3_key != "pending":
                try:
                    delete_screenshot_from_s3(img.s3_key)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"[Celery] Failed to delete image {img.id}: {e}")

        # Get test page for verification file
        test_page = db.query(TestPageRoute).filter(TestPageRoute.id == test_page_id).first()
        if test_page and test_page.verification_file and test_page.verification_file.get('s3_key'):
            try:
                delete_screenshot_from_s3(test_page.verification_file['s3_key'])
                deleted_count += 1
            except Exception as e:
                logger.error(f"[Celery] Failed to delete verification file: {e}")

        logger.info(f"[Celery] Cleaned up {deleted_count} S3 files for test page {test_page_id}")
        return {"success": True, "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"[Celery] Failed to cleanup test page {test_page_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()