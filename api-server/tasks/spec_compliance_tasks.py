# ============================================================================
# Spec Compliance Tasks
# ============================================================================
# Celery tasks for generating spec compliance reports
# ============================================================================

import logging
from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name='tasks.generate_spec_compliance', bind=True)
def generate_spec_compliance(
        self,
        form_page_data: dict,
        paths_data: list,
        spec_data: dict
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

        # Call Claude API
        import anthropic
        import os

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
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