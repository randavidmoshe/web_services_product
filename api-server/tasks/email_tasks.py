"""
Email Tasks - Async email sending via Celery
For scalability: customer emails are sent in background
"""
from celery_app import celery
import logging

logger = logging.getLogger(__name__)


@celery.task(name='tasks.send_email_async', bind=True, max_retries=3)
def send_email_async(self, to_email: str, subject: str, html_body: str, text_body: str = None):
    """
    Send email asynchronously via Celery worker.
    Retries up to 3 times on failure.
    """
    try:
        from services.email_service import send_email
        result = send_email(to_email, subject, html_body, text_body)

        if result.get("success"):
            logger.info(f"Email sent successfully to {to_email}: {subject}")
        else:
            logger.error(f"Email failed to {to_email}: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Email task failed: {str(e)}")
        # Retry with exponential backoff: 60s, 120s, 240s
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery.task(name='tasks.send_verification_email_async')
def send_verification_email_async(to_email: str, to_name: str, verification_token: str):
    """Send verification email asynchronously"""
    try:
        from services.email_service import send_verification_email
        return send_verification_email(to_email, to_name, verification_token)
    except Exception as e:
        logger.error(f"Verification email task failed: {str(e)}")
        return {"success": False, "error": str(e)}


@celery.task(name='tasks.send_invitation_email_async')
def send_invitation_email_async(to_email: str, to_name: str, inviter_name: str, company_name: str, invite_token: str):
    """Send invitation email asynchronously"""
    try:
        from services.email_service import send_invitation_email
        return send_invitation_email(to_email, to_name, inviter_name, company_name, invite_token)
    except Exception as e:
        logger.error(f"Invitation email task failed: {str(e)}")
        return {"success": False, "error": str(e)}


@celery.task(name='tasks.send_password_reset_email_async')
def send_password_reset_email_async(to_email: str, to_name: str, reset_token: str):
    """Send password reset email asynchronously"""
    try:
        from services.email_service import send_password_reset_email
        return send_password_reset_email(to_email, to_name, reset_token)
    except Exception as e:
        logger.error(f"Password reset email task failed: {str(e)}")
        return {"success": False, "error": str(e)}


@celery.task(name='tasks.send_early_access_approved_email_async')
def send_early_access_approved_email_async(to_email: str, to_name: str, company_name: str, daily_budget: float,
                                           trial_days: int):
    """Send early access approval email asynchronously"""
    try:
        from services.email_service import send_early_access_approved_email
        return send_early_access_approved_email(to_email, to_name, company_name, daily_budget, trial_days)
    except Exception as e:
        logger.error(f"Early access approval email task failed: {str(e)}")
        return {"success": False, "error": str(e)}