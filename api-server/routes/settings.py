# routes/settings.py
# User settings endpoints

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from models.database import get_db, User, Company, CompanyProductSubscription
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ApiKeyUpdate(BaseModel):
    api_key: str


class ApiKeyResponse(BaseModel):
    has_key: bool
    masked_key: Optional[str] = None


@router.get("/api-key", response_model=ApiKeyResponse)
async def get_api_key_status(
        user_id: int = Query(None),
        company_id: int = Query(None),
        db: Session = Depends(get_db)
):
    """Get API key status (masked)"""
    if not company_id and user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            company_id = user.company_id

    if not company_id:
        raise HTTPException(status_code=400, detail="company_id or user_id required")

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id
    ).first()

    if not subscription or not subscription.customer_claude_api_key:
        return ApiKeyResponse(has_key=False, masked_key=None)

    key = subscription.customer_claude_api_key
    if len(key) > 12:
        masked = f"{key[:8]}...{key[-4:]}"
    else:
        masked = "****"

    return ApiKeyResponse(has_key=True, masked_key=masked)


@router.put("/api-key")
async def update_api_key(
        payload: ApiKeyUpdate,
        user_id: int = Query(None),
        company_id: int = Query(None),
        db: Session = Depends(get_db)
):
    """Update user's API key (BYOK)"""
    if not company_id and user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            company_id = user.company_id

    if not company_id:
        raise HTTPException(status_code=400, detail="company_id or user_id required")

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

    if not subscription:
        subscription = CompanyProductSubscription(
            company_id=company_id,
            product_id=1,
            status="active",
            customer_claude_api_key=api_key
        )
        db.add(subscription)
    else:
        subscription.customer_claude_api_key = api_key

    company = db.query(Company).filter(Company.id == company_id).first()
    if company:
        company.access_status = 'active'
        if company.account_category:
            company.onboarding_completed = True

    db.commit()

    logger.info(f"[Settings] API key updated for company {company_id}")

    return {"success": True, "message": "API key saved successfully"}


@router.delete("/api-key")
async def delete_api_key(
        user_id: int = Query(None),
        company_id: int = Query(None),
        db: Session = Depends(get_db)
):
    """Delete user's API key"""
    if not company_id and user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            company_id = user.company_id

    if not company_id:
        raise HTTPException(status_code=400, detail="company_id or user_id required")

    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company_id
    ).first()

    if subscription:
        subscription.customer_claude_api_key = None
        db.commit()

    logger.info(f"[Settings] API key deleted for company {company_id}")

    return {"success": True, "message": "API key removed"}