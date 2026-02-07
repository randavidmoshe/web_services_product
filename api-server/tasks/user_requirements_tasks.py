# ============================================================================
# User Requirements Celery Tasks
# ============================================================================

import json
import logging
import os
from services.encryption_service import get_decrypted_api_key
import re
from typing import Dict, Any
from celery import shared_task

logger = logging.getLogger(__name__)


def _get_redis_client():
    """Get Redis client with connection pooling"""
    import redis
    pool = redis.ConnectionPool(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        max_connections=50
    )
    return redis.Redis(connection_pool=pool)


def _get_db_session():
    """Get database session"""
    from models.database import SessionLocal
    return SessionLocal()


def _check_budget_and_get_api_key(db, company_id: int, product_id: int) -> str:
    """Check budget and get API key."""
    from services.ai_budget_service import get_budget_service, BudgetExceededError
    from models.database import CompanyProductSubscription

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
        # Decrypt the API key (uses Redis cache for performance)
        return get_decrypted_api_key(company_id, subscription.customer_claude_api_key)
    return os.getenv("ANTHROPIC_API_KEY")


def _record_usage(db, company_id: int, product_id: int, user_id: int,
                  operation_type, input_tokens: int, output_tokens: int):
    """Record AI usage after successful call"""
    from services.ai_budget_service import get_budget_service

    redis_client = _get_redis_client()
    budget_service = get_budget_service(redis_client)

    return budget_service.record_usage(
        db=db,
        company_id=company_id,
        product_id=product_id,
        user_id=user_id,
        operation_type=operation_type,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def parse_user_inputs(
        self,
        form_page_route_id: int,
        content: str,
        file_type: str = "txt",
        company_id: int = None,
        product_id: int = 1,
        user_id: int = None
) -> Dict[str, Any]:
    """
    Parse user-provided inputs file content into structured format using AI.
    Updates DB directly when done.
    """
    from services.ai_budget_service import AIOperationType, BudgetExceededError
    from models.database import FormPageRoute

    logger.info(f"[UserInputs] Parsing {file_type} content ({len(content)} chars) for form_page {form_page_route_id}")

    db = _get_db_session()

    try:
        # Get form page route
        form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
        if not form_page:
            logger.error(f"[UserInputs] Form page route {form_page_route_id} not found")
            return {"success": False, "error": "Form page route not found"}

        # Try JSON parse directly first (no AI needed)
        if file_type == "json":
            try:
                parsed = json.loads(content)
                if "field_values" in parsed or "file_paths" in parsed:
                    logger.info(f"[UserInputs] Parsed JSON directly (no AI call)")
                    inputs = _normalize_inputs(parsed)
                    inputs["status"] = "ready"
                    form_page.user_provided_inputs = inputs
                    db.commit()
                    return {"success": True, "inputs": inputs}
            except json.JSONDecodeError:
                pass

        # Get API key with budget check
        if company_id:
            api_key = _check_budget_and_get_api_key(db, company_id, product_id)
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            form_page.user_provided_inputs = {"status": "error", "error": "No API key available"}
            db.commit()
            return {"success": False, "error": "No API key available"}

        # Call AI to parse
        inputs, input_tokens, output_tokens = _parse_with_ai(content, file_type, api_key)

        if inputs:
            # Record usage
            if company_id:
                _record_usage(
                    db, company_id, product_id, user_id or 0,
                    AIOperationType.FORM_MAPPER_ANALYZE,
                    input_tokens, output_tokens
                )

            inputs["status"] = "ready"
            form_page.user_provided_inputs = inputs
            db.commit()

            logger.info(f"[UserInputs] Parsed {len(inputs.get('field_values', []))} field values, "
                        f"{len(inputs.get('file_paths', []))} file paths")
            return {"success": True, "inputs": inputs}
        else:
            form_page.user_provided_inputs = {"status": "error", "error": "AI failed to parse inputs"}
            db.commit()
            return {"success": False, "error": "AI failed to parse inputs"}

    except BudgetExceededError as e:
        logger.warning(f"[UserInputs] Budget exceeded for company {e.company_id}")
        try:
            form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
            if form_page:
                form_page.user_provided_inputs = {"status": "error", "error": "AI budget exceeded"}
                db.commit()
        except:
            pass
        return {"success": False, "error": "AI budget exceeded", "budget_exceeded": True}

    except Exception as e:
        logger.error(f"[UserInputs] Error parsing: {e}", exc_info=True)
        try:
            form_page = db.query(FormPageRoute).filter(FormPageRoute.id == form_page_route_id).first()
            if form_page:
                form_page.user_provided_inputs = {"status": "error", "error": str(e)}
                db.commit()
        except:
            pass
        if self.request.retries < self.max_retries:
            raise  # Will retry
        return {"success": False, "error": str(e)}

    finally:
        db.close()


def _parse_with_ai(content: str, file_type: str, api_key: str) -> tuple:
    """
    Use Claude AI to parse inputs content.
    Returns: (parsed_inputs, input_tokens, output_tokens)
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Parse this user-provided form input requirements into structured JSON.

**Input ({file_type}):**
```
{content}
```

**Output format - return ONLY valid JSON:**
```json
{{
  "field_values": [
    {{"field_hint": "field name as shown in form", "value": "the value to use"}}
  ],
  "file_paths": [
    {{"field_hint": "file upload field name", "path": "full desktop path"}}
  ]
}}
```

**Rules:**
1. `field_values` = text/number values (DB port, username, license key, etc.)
2. `file_paths` = file paths for upload fields (configs, certificates, etc.)
3. `field_hint` should match how field appears in the form
4. Keep paths exactly as provided (with backslashes for Windows)
5. Return ONLY the JSON, no other text
"""

    try:
        logger.info("[UserInputs] Calling Claude API...")

        message = client.messages.create(
            #model="claude-haiku-4-5-20251001",
            model = "claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        logger.info(f"[UserInputs] AI response ({len(response_text)} chars, {input_tokens}+{output_tokens} tokens)")

        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            return _normalize_inputs(parsed), input_tokens, output_tokens

        logger.error("[UserInputs] No JSON found in AI response")
        return None, input_tokens, output_tokens

    except Exception as e:
        logger.error(f"[UserInputs] AI parsing error: {e}")
        return None, 0, 0


def _normalize_inputs(parsed: Dict) -> Dict:
    """Normalize parsed inputs to consistent structure."""
    return {
        "field_values": [
            {"field_hint": fv.get("field_hint", ""), "value": fv.get("value", "")}
            for fv in parsed.get("field_values", [])
        ],
        "file_paths": [
            {"field_hint": fp.get("field_hint", ""), "path": fp.get("path", fp.get("desktop_path", ""))}
            for fp in parsed.get("file_paths", [])
        ]
    }