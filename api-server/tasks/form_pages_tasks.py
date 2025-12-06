"""
Celery tasks for Form Pages Discovery session management.
"""
import logging
from celery import shared_task
from models.database import SessionLocal

logger = logging.getLogger(__name__)


def _get_db_session():
    return SessionLocal()


@shared_task(name="tasks.cleanup_stale_crawl_sessions")
def cleanup_stale_crawl_sessions(timeout_hours: int = 2):
    """Cleanup stale form pages discovery sessions"""
    db = _get_db_session()
    try:
        from models.database import CrawlSession
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)

        stale_sessions = db.query(CrawlSession).filter(
            CrawlSession.status.in_(["pending", "running", "in_progress"]),
            CrawlSession.created_at < cutoff
        ).all()

        count = len(stale_sessions)
        for session in stale_sessions:
            session.status = "failed"
            session.error_message = f"Timed out after {timeout_hours} hours"

        db.commit()
        logger.info(f"[FormPagesTasks] Cleaned up {count} stale crawl sessions")
        return {"cleaned": count}
    except Exception as e:
        logger.error(f"[FormPagesTasks] Cleanup failed: {e}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()