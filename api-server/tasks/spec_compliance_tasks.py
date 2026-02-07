# ============================================================================
# Spec Compliance Tasks
# ============================================================================
# Celery tasks for generating spec compliance reports
# ============================================================================

import logging
from celery_app import celery

import os
from models.database import SessionLocal, CompanyProductSubscription
from services.encryption_service import get_decrypted_api_key
from services.ai_budget_service import get_budget_service, BudgetExceededError
import redis

logger = logging.getLogger(__name__)


def _get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0
    )


def _get_api_key(company_id: int, product_id: int = 1) -> str:
    """Get API key - BYOK if available, otherwise system key"""
    db = SessionLocal()
    try:
        redis_client = _get_redis_client()
        budget_service = get_budget_service(redis_client)

        has_budget, remaining, total = budget_service.check_budget(db, company_id, product_id)
        if not has_budget:
            raise BudgetExceededError(company_id, total, total - remaining)

        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()

        if subscription and subscription.customer_claude_api_key:
            return get_decrypted_api_key(company_id, subscription.customer_claude_api_key)

        return os.getenv("ANTHROPIC_API_KEY")
    finally:
        db.close()

@celery.task(name='tasks.generate_spec_compliance', bind=True)
def generate_spec_compliance(
        self,
        form_page_data: dict,
        paths_data: list,
        spec_data: dict,
        company_id: int = None,
        product_id: int = 1
):
    """
    Generate a spec compliance report by comparing spec document with actual paths
    """
    try:
        self.update_state(state='PROCESSING', meta={'progress': 10, 'message': 'Analyzing spec document...'})

        from services.ai_spec_compliance_prompter import build_spec_compliance_prompt

        # Build the prompt
        prompt = build_spec_compliance_prompt(
            form_page_data=form_page_data,
            paths_data=paths_data,
            spec_content=spec_data.get('content', '')
        )

        self.update_state(state='PROCESSING', meta={'progress': 30, 'message': 'Sending to AI...'})

        # Get API key (BYOK or system)
        import anthropic

        if company_id:
            api_key = _get_api_key(company_id, product_id)
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")

        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            #model="claude-sonnet-4-20250514",
            model = "claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )

        self.update_state(state='PROCESSING', meta={'progress': 80, 'message': 'Processing response...'})

        report = response.content[0].text

        # Parse summary from report (look for counts)
        summary = {
            "compliant": report.lower().count("✅"),
            "non_compliant": report.lower().count("❌"),
            "warnings": report.lower().count("⚠️")
        }

        self.update_state(state='PROCESSING', meta={'progress': 100, 'message': 'Complete'})

        return {
            'success': True,
            'report': report,
            'summary': summary
        }

    except Exception as e:
        logger.error(f"Spec compliance generation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'report': '',
            'summary': {}
        }