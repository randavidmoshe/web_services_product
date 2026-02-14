# routes/settings.py
# User settings endpoints

from fastapi import APIRouter, Depends, HTTPException, Request
from utils.auth_helpers import get_current_user_from_request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from models.database import get_db, User, Company, CompanyProductSubscription
import logging
from services.encryption_service import encrypt_secret, decrypt_secret, invalidate_cached_secret, mask_api_key
import redis
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ApiKeyUpdate(BaseModel):
    api_key: str


class ApiKeyResponse(BaseModel):
    has_key: bool
    masked_key: Optional[str] = None


@router.get("/api-key", response_model=ApiKeyResponse)
async def get_api_key_status(
        request: Request,
        db: Session = Depends(get_db)
):
    """Get API key status (masked) - Admin only"""
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    company_id = current_user["company_id"]

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id
    ).first()

    if not subscription or not subscription.customer_claude_api_key:
        return ApiKeyResponse(has_key=False, masked_key=None)

    # Decrypt to create masked version (never return full key)
    try:
        encrypted_key = subscription.customer_claude_api_key
        decrypted_key = decrypt_secret(encrypted_key, company_id)
        masked = mask_api_key(decrypted_key)
    except Exception as e:
        logger.warning(f"[Settings] Could not decrypt API key for company {company_id}: {e}")
        masked = "****"

    return ApiKeyResponse(has_key=True, masked_key=masked)


@router.put("/api-key")
async def update_api_key(
        payload: ApiKeyUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    """Update company's API key (BYOK) - Admin only"""
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    company_id = current_user["company_id"]

    api_key = payload.api_key.strip()
    if not api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format. Anthropic keys start with 'sk-ant-'"
        )

    if len(api_key) < 40:
        raise HTTPException(
            status_code=400,
            detail="API key appears too short"
        )

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id
    ).first()

    # Encrypt the API key before storing
    try:
        encrypted_key = encrypt_secret(api_key, company_id)
    except Exception as e:
        logger.error(f"[Settings] Failed to encrypt API key for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to encrypt API key")

    if not subscription:
        subscription = CompanyProductSubscription(
            company_id=company_id,
            product_id=1,
            status="active",
            customer_claude_api_key=encrypted_key
        )
        db.add(subscription)
    else:
        subscription.customer_claude_api_key = encrypted_key

    # Invalidate cache so next read gets fresh decrypted value
    invalidate_cached_secret(company_id, "api_key")

    company = db.query(Company).filter(Company.id == company_id).first()
    if company:
        company.access_model = 'byok'
        company.access_status = 'active'
        if company.account_category:
            company.onboarding_completed = True

    db.commit()

    # Invalidate AI access/budget caches (same pattern as company.py)
    try:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )
        redis_client.delete(f"ai_access:{company_id}")
        redis_client.delete(f"ai_daily_budget:{company_id}")
    except Exception:
        pass

    logger.info(f"[Settings] API key updated for company {company_id}")

    return {"success": True, "message": "API key saved successfully"}


@router.delete("/api-key")
async def delete_api_key(
        request: Request,
        db: Session = Depends(get_db)
):
    """Delete company's API key - Admin only"""
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    company_id = current_user["company_id"]

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id
    ).first()

    if subscription:
        subscription.customer_claude_api_key = None
        db.commit()
        # Invalidate cache
        invalidate_cached_secret(company_id, "api_key")

    logger.info(f"[Settings] API key deleted for company {company_id}")

    return {"success": True, "message": "API key removed"}