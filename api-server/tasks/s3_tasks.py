"""
S3 and Activity Log Tasks - Celery tasks for S3 operations and log processing
Location: api-server/tasks/s3_tasks.py

Scalable: All heavy operations happen in Celery workers, not in API handlers.
"""

import os
import json
import logging
from celery import shared_task
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Log size threshold for S3 upload (50KB)
LOG_SIZE_THRESHOLD_BYTES = 50 * 1024


def _get_db_session():
    """Get database session"""
    from models.database import SessionLocal
    return SessionLocal()


def _get_company_kms_key(db, company_id: int) -> Optional[str]:
    """Get company's KMS key ARN for BYOK encryption."""
    from models.database import Company
    company = db.query(Company).filter(Company.id == company_id).first()
    return company.kms_key_arn if company else None


# ============================================================================
# Log Processing Tasks
# ============================================================================

@shared_task(name="tasks.process_activity_logs")
def process_activity_logs_task(
        entries_json: str,
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int,
        user_id: int = None
) -> Dict:
    """
    Process activity log entries and insert to DB.
    Called for small logs (< 50KB) sent directly as JSON.

    Args:
        entries_json: JSON string of log entries
        activity_type: 'discovery', 'mapping', 'test_run'
        session_id: Session ID
        project_id: Project ID
        company_id: Company ID
        user_id: Optional user ID
    """
    from models.database import ActivityLogEntry

    db = _get_db_session()

    try:
        entries = json.loads(entries_json)

        # Determine session ID field
        crawl_session_id = session_id if activity_type == "discovery" else None
        mapper_session_id = session_id if activity_type == "mapping" else None
        test_run_id = session_id if activity_type == "test_run" else None

        entries_created = 0
        for entry_data in entries:
            # Parse timestamp
            try:
                timestamp = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()

            entry = ActivityLogEntry(
                company_id=company_id,
                project_id=project_id,
                user_id=user_id,
                activity_type=activity_type,
                crawl_session_id=crawl_session_id,
                mapper_session_id=mapper_session_id,
                test_run_id=test_run_id,
                timestamp=timestamp,
                level=entry_data.get('level', 'info'),
                category=entry_data.get('category', 'milestone'),
                message=entry_data.get('message', ''),
                extra_data=entry_data.get('extra_data')
            )
            db.add(entry)
            entries_created += 1

        db.commit()

        logger.info(f"[LogTask] Inserted {entries_created} log entries for {activity_type} session {session_id}")

        return {
            "success": True,
            "entries_created": entries_created,
            "activity_type": activity_type,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"[LogTask] Failed to process logs: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="tasks.process_activity_logs_from_s3")
def process_activity_logs_from_s3_task(
        s3_key: str,
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int,
        user_id: int = None
) -> Dict:
    """
    Process activity log entries from S3 file and insert to DB.
    Called for large logs (>= 50KB) uploaded to S3.

    Args:
        s3_key: S3 key where log JSON is stored
        activity_type: 'discovery', 'mapping', 'test_run'
        session_id: Session ID
        project_id: Project ID
        company_id: Company ID
        user_id: Optional user ID
    """
    from models.database import ActivityLogEntry
    from services.s3_storage import get_s3_file_content, delete_screenshot_from_s3

    db = _get_db_session()

    try:
        # Read log file from S3
        content = get_s3_file_content(s3_key)
        entries = json.loads(content.decode('utf-8'))

        # Determine session ID field
        crawl_session_id = session_id if activity_type == "discovery" else None
        mapper_session_id = session_id if activity_type == "mapping" else None
        test_run_id = session_id if activity_type == "test_run" else None

        entries_created = 0
        for entry_data in entries:
            try:
                timestamp = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()

            entry = ActivityLogEntry(
                company_id=company_id,
                project_id=project_id,
                user_id=user_id,
                activity_type=activity_type,
                crawl_session_id=crawl_session_id,
                mapper_session_id=mapper_session_id,
                test_run_id=test_run_id,
                timestamp=timestamp,
                level=entry_data.get('level', 'info'),
                category=entry_data.get('category', 'milestone'),
                message=entry_data.get('message', ''),
                extra_data=entry_data.get('extra_data')
            )
            db.add(entry)
            entries_created += 1

        db.commit()

        # Delete temp log file from S3 after processing
        delete_screenshot_from_s3(s3_key)

        logger.info(
            f"[LogTask] Inserted {entries_created} log entries from S3 for {activity_type} session {session_id}")

        return {
            "success": True,
            "entries_created": entries_created,
            "activity_type": activity_type,
            "session_id": session_id,
            "source": "s3"
        }

    except Exception as e:
        logger.error(f"[LogTask] Failed to process logs from S3: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


# ============================================================================
# Screenshot Record Tasks
# ============================================================================

@shared_task(name="tasks.record_screenshots_uploaded")
def record_screenshots_uploaded_task(
        screenshots: List[Dict],
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int
) -> Dict:
    """
    Record uploaded screenshots in database.
    Called after agent confirms successful S3 uploads.

    Args:
        screenshots: List of {s3_key, filename, file_size_bytes}
        activity_type: 'mapping' or 'test_run'
        session_id: Session ID
        project_id: Project ID
        company_id: Company ID
    """
    from models.database import ActivityScreenshot

    db = _get_db_session()

    try:
        records_created = 0
        for screenshot in screenshots:
            record = ActivityScreenshot(
                company_id=company_id,
                project_id=project_id,
                activity_type=activity_type,
                session_id=session_id,
                s3_key=screenshot['s3_key'],
                filename=screenshot['filename'],
                file_size_bytes=screenshot.get('file_size_bytes')
            )
            db.add(record)
            records_created += 1

        db.commit()

        logger.info(f"[S3Task] Recorded {records_created} screenshots for {activity_type} session {session_id}")

        return {
            "success": True,
            "records_created": records_created
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to record screenshots: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


# ============================================================================
# Cleanup Tasks
# ============================================================================

@shared_task(name="tasks.delete_s3_folder")
def delete_s3_folder_task(
        prefix: str,
        company_id: int,
        project_id: int,
        reason: str = "cleanup"
) -> Dict:
    """
    Delete all S3 objects with given prefix.
    Used for cleanup on remap/delete.
    """
    from services.s3_storage import delete_s3_folder

    try:
        deleted_count = delete_s3_folder(prefix)

        logger.info(f"[S3Task] Deleted {deleted_count} objects from {prefix} (reason: {reason})")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "prefix": prefix,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to delete folder {prefix}: {e}")
        return {
            "success": False,
            "error": str(e),
            "prefix": prefix
        }


@shared_task(name="tasks.cleanup_form_s3_files")
def cleanup_form_s3_files_task(
        company_id: int,
        project_id: int,
        form_page_route_id: int,
        reason: str = "remap"
) -> Dict:
    """
    Delete all S3 files associated with a form page route.
    Called on remap or form deletion.
    """
    from services.s3_storage import delete_s3_folder
    from models.database import FormUploadedFile

    db = _get_db_session()

    try:
        # Delete from S3
        prefix = f"form_files/{company_id}/{project_id}/{form_page_route_id}/"
        deleted_s3 = delete_s3_folder(prefix)

        # Delete DB records
        deleted_db = db.query(FormUploadedFile).filter(
            FormUploadedFile.form_page_route_id == form_page_route_id
        ).delete()

        db.commit()

        logger.info(f"[S3Task] Cleaned up form {form_page_route_id}: {deleted_s3} S3 objects, {deleted_db} DB records")

        return {
            "success": True,
            "deleted_s3_objects": deleted_s3,
            "deleted_db_records": deleted_db,
            "form_page_route_id": form_page_route_id,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to cleanup form {form_page_route_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="tasks.cleanup_session_screenshots")
def cleanup_session_screenshots_task(
        company_id: int,
        project_id: int,
        activity_type: str,
        session_id: int,
        reason: str = "session_deleted"
) -> Dict:
    """
    Delete all screenshots for a session.
    Called when session is deleted.
    """
    from services.s3_storage import delete_s3_folder
    from models.database import ActivityScreenshot

    db = _get_db_session()

    try:
        # Delete from S3
        prefix = f"{activity_type}/{company_id}/{project_id}/{session_id}/"
        deleted_s3 = delete_s3_folder(prefix)

        # Delete DB records
        deleted_db = db.query(ActivityScreenshot).filter(
            ActivityScreenshot.activity_type == activity_type,
            ActivityScreenshot.session_id == session_id
        ).delete()

        db.commit()

        logger.info(f"[S3Task] Cleaned up session {session_id}: {deleted_s3} S3 objects, {deleted_db} DB records")

        return {
            "success": True,
            "deleted_s3_objects": deleted_s3,
            "deleted_db_records": deleted_db
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to cleanup session {session_id}: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="tasks.process_screenshot_zip")
def process_screenshot_zip_task(
        s3_key: str,
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int
) -> Dict:
    """
    Process uploaded screenshot zip: download, unzip, re-upload individual files.

    Used by: Celery method (docker-compose development)
    Not used by: Lambda method (AWS production)

    Args:
        s3_key: S3 key of the uploaded zip (e.g., screenshots_temp/1/5/mapping_606.zip)
        activity_type: 'mapping' or 'test_run'
        session_id: Session ID
        project_id: Project ID
        company_id: Company ID
    """
    import io
    import zipfile
    from services.s3_storage import get_s3_file_content, delete_screenshot_from_s3, s3_client, S3_BUCKET
    from models.database import ActivityScreenshot

    logger.info(f"[S3Task] Processing screenshot zip: {s3_key}")

    db = _get_db_session()

    try:
        # Download zip from S3
        logger.info(f"[S3Task] Downloading zip: {s3_key}")
        zip_content = get_s3_file_content(s3_key)

        if not zip_content:
            logger.error(f"[S3Task] Failed to download zip: {s3_key}")
            return {"success": False, "error": "Failed to download zip"}

        logger.info(f"[S3Task] Downloaded zip: {len(zip_content)} bytes")

        # Extract and re-upload each file
        zip_buffer = io.BytesIO(zip_content)
        records_created = 0

        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            for filename in zip_file.namelist():
                if not filename.lower().endswith('.png'):
                    continue

                # Extract file
                file_content = zip_file.read(filename)
                file_size = len(file_content)

                # Upload to final location
                final_s3_key = f"screenshots/{company_id}/{project_id}/{session_id}/{filename}"

                logger.info(f"[S3Task] Uploading: {final_s3_key}")

                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=final_s3_key,
                    Body=file_content,
                    ContentType='image/png'
                )

                # Record in DB
                record = ActivityScreenshot(
                    company_id=company_id,
                    project_id=project_id,
                    activity_type=activity_type,
                    session_id=session_id,
                    s3_key=final_s3_key,
                    filename=filename,
                    file_size_bytes=file_size
                )
                db.add(record)
                records_created += 1

        db.commit()

        # Delete temp zip from S3
        logger.info(f"[S3Task] Deleting temp zip: {s3_key}")
        delete_screenshot_from_s3(s3_key)

        logger.info(f"[S3Task] Processed zip: {records_created} screenshots for {activity_type} session {session_id}")

        return {
            "success": True,
            "records_created": records_created,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to process screenshot zip: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="tasks.process_form_files_zip")
def process_form_files_zip_task(
        s3_key: str,
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int,
        form_page_route_id: int
) -> Dict:
    """
    Process uploaded form files zip: download, unzip, re-upload individual files.

    Used by: Celery method (docker-compose development)
    Not used by: Lambda method (AWS production)

    Args:
        s3_key: S3 key of the uploaded zip (e.g., form_files_temp/1/5/182.zip)
        activity_type: 'mapping'
        session_id: Session ID
        project_id: Project ID
        company_id: Company ID
        form_page_route_id: Form page route ID
    """
    import io
    import zipfile
    from services.s3_storage import get_s3_file_content, delete_screenshot_from_s3, s3_client, S3_BUCKET
    from models.database import FormUploadedFile

    logger.info(f"[S3Task] Processing form files zip: {s3_key}")

    db = _get_db_session()

    try:
        # Download zip from S3
        logger.info(f"[S3Task] Downloading zip: {s3_key}")
        zip_content = get_s3_file_content(s3_key)

        if not zip_content:
            logger.error(f"[S3Task] Failed to download zip: {s3_key}")
            return {"success": False, "error": "Failed to download zip"}

        logger.info(f"[S3Task] Downloaded zip: {len(zip_content)} bytes")

        # Extract and re-upload each file
        zip_buffer = io.BytesIO(zip_content)
        records_created = 0

        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            for filename in zip_file.namelist():
                # Skip directories
                if filename.endswith('/'):
                    continue

                # Extract file
                file_content = zip_file.read(filename)
                file_size = len(file_content)

                # Determine content type
                content_type = 'application/octet-stream'
                if filename.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif filename.lower().endswith('.png'):
                    content_type = 'image/png'
                elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    content_type = 'image/jpeg'
                elif filename.lower().endswith('.txt'):
                    content_type = 'text/plain'

                # Upload to final location
                final_s3_key = f"form_files/{company_id}/{project_id}/{form_page_route_id}/{filename}"

                logger.info(f"[S3Task] Uploading: {final_s3_key}")

                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=final_s3_key,
                    Body=file_content,
                    ContentType=content_type
                )

                # Record in DB
                record = FormUploadedFile(
                    company_id=company_id,
                    project_id=project_id,
                    form_page_route_id=form_page_route_id,
                    s3_key=final_s3_key,
                    filename=filename,
                    file_size_bytes=file_size
                )
                db.add(record)
                records_created += 1

        db.commit()

        # Delete temp zip from S3
        logger.info(f"[S3Task] Deleting temp zip: {s3_key}")
        delete_screenshot_from_s3(s3_key)

        logger.info(f"[S3Task] Processed form files zip: {records_created} files for form route {form_page_route_id}")

        return {
            "success": True,
            "records_created": records_created,
            "form_page_route_id": form_page_route_id
        }

    except Exception as e:
        logger.error(f"[S3Task] Failed to process form files zip: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


@shared_task(name="tasks.delete_s3_files")
def delete_s3_files_task(s3_keys: List[str]) -> Dict:
    """
    Delete multiple files from S3.

    Args:
        s3_keys: List of S3 keys to delete
    """
    from services.s3_storage import s3_client, S3_BUCKET

    logger.info(f"[S3Task] Deleting {len(s3_keys)} files from S3")

    deleted = 0
    errors = []

    for s3_key in s3_keys:
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            deleted += 1
        except Exception as e:
            errors.append(f"{s3_key}: {str(e)}")
            logger.error(f"[S3Task] Failed to delete {s3_key}: {e}")

    logger.info(f"[S3Task] Deleted {deleted}/{len(s3_keys)} files")

    return {
        "success": len(errors) == 0,
        "deleted": deleted,
        "total": len(s3_keys),
        "errors": errors if errors else None
    }