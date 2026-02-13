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


@shared_task(name="tasks.trigger_logout_mapping_after_discovery")
def trigger_logout_mapping_after_discovery(network_id: int, user_id: int, company_id: int):
    """
    After discovery completes, trigger logout mapping via orchestrator.
    Runs as Celery task for scalability (non-blocking).
    Security: credentials loaded server-side from DB, never sent to agent.
    """
    db = _get_db_session()
    try:
        from models.database import Network
        from services.form_mapper_orchestrator import FormMapperOrchestrator
        from models.form_mapper_models import FormMapperSession

        network = db.query(Network).filter(Network.id == network_id).first()
        if not network:
            logger.warning(f"[LogoutMapping] Network {network_id} not found")
            return {"success": False, "error": "Network not found"}

        # Create mapper DB session
        mapper_db_session = FormMapperSession(
            network_id=network_id,
            user_id=user_id,
            company_id=company_id,
            status="initializing",
            config={"mapping_type": "logout_mapping"}
        )
        db.add(mapper_db_session)
        db.commit()
        db.refresh(mapper_db_session)

        # Create orchestrator session and start
        orchestrator = FormMapperOrchestrator(db)
        orchestrator.create_session(
            session_id=str(mapper_db_session.id),
            user_id=user_id,
            network_id=network_id,
            company_id=company_id,
            product_id=network.product_id,
            project_id=network.project_id,
            mapping_type="logout_mapping",
            base_url=network.url
        )

        result = orchestrator.start_login_phase(session_id=str(mapper_db_session.id))
        if not result.get("success"):
            logger.error(f"[LogoutMapping] Failed to start logout mapping: {result}")
            return {"success": False, "error": "Failed to start logout mapping"}

        logger.info(f"[LogoutMapping] Logout mapping started for network {network_id}, session {mapper_db_session.id}")
        return {"success": True, "session_id": str(mapper_db_session.id)}

    except Exception as e:
        logger.error(f"[LogoutMapping] Error: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()