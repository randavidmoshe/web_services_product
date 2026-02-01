from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.database import get_db, Company, User, CompanyProductSubscription
from utils.auth_helpers import verify_user_access

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class SetCategoryRequest(BaseModel):
    account_category: str  # 'form_centric' or 'dynamic'


class SetAccessModelRequest(BaseModel):
    access_model: str  # 'byok' or 'early_access'
    claude_api_key: Optional[str] = None  # Required if byok


@router.get("/status")
async def get_onboarding_status(
        user_id: int,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Get current onboarding status for a user's company."""
    user = verify_user_access(authorization, user_id, db)

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "onboarding_completed": company.onboarding_completed or False,
        "account_category": company.account_category,
        "access_model": company.access_model,
        "access_status": company.access_status or 'pending',
        "daily_ai_budget": company.daily_ai_budget or 10.0,
        "trial_days_total": company.trial_days_total or 10,
        "trial_start_date": company.trial_start_date.isoformat() if company.trial_start_date else None
    }


@router.post("/category")
async def set_account_category(
        request: SetCategoryRequest,
        user_id: int,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Set account category (form_centric or dynamic)."""
    if request.account_category not in ('form_centric', 'dynamic'):
        raise HTTPException(status_code=400, detail="Invalid category. Must be 'form_centric' or 'dynamic'")

    user = verify_user_access(authorization, user_id, db)

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.account_category = request.account_category
    db.commit()

    return {
        "status": "success",
        "account_category": company.account_category
    }


@router.post("/access-model")
async def set_access_model(
        request: SetAccessModelRequest,
        user_id: int,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Set access model (byok or early_access)."""
    if request.access_model not in ('byok', 'early_access'):
        raise HTTPException(status_code=400, detail="Invalid access model. Must be 'byok' or 'early_access'")

    if request.access_model == 'byok' and not request.claude_api_key:
        raise HTTPException(status_code=400, detail="API key required for BYOK")

    user = verify_user_access(authorization, user_id, db)

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Update company
    company.access_model = request.access_model

    if request.access_model == 'byok':
        company.access_status = 'active'
        # Store API key in subscription
        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company.id
        ).first()
        if subscription:
            subscription.customer_claude_api_key = request.claude_api_key
    else:
        # Early Access - pending until super admin approves
        company.access_status = 'pending'

    db.commit()

    return {
        "status": "success",
        "access_model": company.access_model,
        "access_status": company.access_status
    }


@router.post("/complete")
async def complete_onboarding(
        user_id: int,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Mark onboarding as complete. Only succeeds if access is usable."""
    user = verify_user_access(authorization, user_id, db)

    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check requirements
    if not company.account_category:
        raise HTTPException(status_code=400, detail="Account category not set")

    if not company.access_model:
        raise HTTPException(status_code=400, detail="Access model not set")

    if company.access_status != 'active':
        raise HTTPException(status_code=400, detail="Access not yet approved")

    company.onboarding_completed = True
    db.commit()

    return {
        "status": "success",
        "onboarding_completed": True
    }