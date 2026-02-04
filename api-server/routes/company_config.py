# company_config.py
# API routes for super admin to manage company Form Mapper configuration

from fastapi import APIRouter, Depends, HTTPException, status, Request
from utils.auth_helpers import get_current_user_from_request
from sqlalchemy.orm import Session
from typing import List, Optional

from models.database import get_db, Company, SuperAdmin
from models.form_mapper_config_models import (
    FormMapperConfig,
    FormMapperConfigUpdate,
    DEFAULT_FORM_MAPPER_CONFIG,
    get_company_config,
    update_company_config
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/companies", tags=["Company Config"])


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class CompanyConfigResponse(BaseModel):
    company_id: int
    company_name: str
    form_mapper_config: FormMapperConfig


class CompanyListResponse(BaseModel):
    total: int
    companies: List[CompanyConfigResponse]


class UsageBreakdownItem(BaseModel):
    operation_type: str
    count: int
    total_tokens: int
    total_cost: float


class CompanyUsageResponse(BaseModel):
    company_id: int
    company_name: str
    monthly_budget: float
    used_this_month: float
    remaining: float
    budget_reset_date: Optional[str]
    breakdown: List[UsageBreakdownItem]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/{company_id}/form-mapper-config", response_model=CompanyConfigResponse)
def get_company_form_mapper_config(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get Form Mapper configuration for a company.
    Super admin only.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    config = get_company_config(db, company_id)
    
    return CompanyConfigResponse(
        company_id=company.id,
        company_name=company.name,
        form_mapper_config=config
    )


@router.put("/{company_id}/form-mapper-config", response_model=CompanyConfigResponse)
def update_company_form_mapper_config(
    company_id: int,
    config_update: FormMapperConfigUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update Form Mapper configuration for a company.
    Super admin only. Only provided fields are updated.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    try:
        updated_config = update_company_config(db, company_id, config_update)
        
        return CompanyConfigResponse(
            company_id=company.id,
            company_name=company.name,
            form_mapper_config=updated_config
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{company_id}/form-mapper-config/reset", response_model=CompanyConfigResponse)
def reset_company_form_mapper_config(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Reset Form Mapper configuration to defaults for a company.
    Super admin only.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    # Reset to defaults
    company.form_mapper_config = DEFAULT_FORM_MAPPER_CONFIG.copy()
    db.commit()
    
    return CompanyConfigResponse(
        company_id=company.id,
        company_name=company.name,
        form_mapper_config=FormMapperConfig(**DEFAULT_FORM_MAPPER_CONFIG)
    )


@router.get("/", response_model=CompanyListResponse)
def list_companies_with_config(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List all companies with their Form Mapper configuration.
    Super admin only.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    total = db.query(Company).count()
    companies = db.query(Company).offset(skip).limit(limit).all()
    
    result = []
    for company in companies:
        config = get_company_config(db, company.id)
        result.append(CompanyConfigResponse(
            company_id=company.id,
            company_name=company.name,
            form_mapper_config=config
        ))
    
    return CompanyListResponse(
        total=total,
        companies=result
    )


@router.get("/defaults", response_model=FormMapperConfig)
def get_default_config():
    """
    Get default Form Mapper configuration values.
    Useful for UI to show defaults.
    """
    return FormMapperConfig(**DEFAULT_FORM_MAPPER_CONFIG)


# ============================================================
# AI USAGE / BUDGET ENDPOINTS
# ============================================================

@router.get("/{company_id}/ai-usage", response_model=CompanyUsageResponse)
def get_company_ai_usage(
    company_id: int,
    request: Request,
    product_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Get AI usage summary for a company.
    Super admin only.
    
    Shows monthly budget, current usage, and breakdown by operation type.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found"
        )
    
    try:
        from services.ai_budget_service import get_budget_service
        import redis
        import os
        
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )
        
        budget_service = get_budget_service(redis_client)
        summary = budget_service.get_company_usage_summary(db, company_id, product_id)
        
        if "error" in summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=summary["error"]
            )
        
        return CompanyUsageResponse(
            company_id=company_id,
            company_name=company.name,
            monthly_budget=summary.get("monthly_budget", 0),
            used_this_month=summary.get("used_this_month", 0),
            remaining=summary.get("remaining", 0),
            budget_reset_date=summary.get("budget_reset_date"),
            breakdown=[
                UsageBreakdownItem(
                    operation_type=item["operation_type"],
                    count=item["count"],
                    total_tokens=item["total_tokens"] or 0,
                    total_cost=item["total_cost"] or 0
                )
                for item in summary.get("breakdown", [])
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/ai-usage/all")
def get_all_companies_ai_usage(
    request: Request,
    product_id: int = 1,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get AI usage summary for all companies.
    Super admin only.
    
    Useful for monitoring system-wide AI costs.
    """
    current_user = get_current_user_from_request(request)
    if current_user["type"] not in ["super_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from models.database import CompanyProductSubscription
    from sqlalchemy import func
    
    # Get all subscriptions with usage
    subscriptions = db.query(
        CompanyProductSubscription,
        Company.name.label("company_name")
    ).join(
        Company, CompanyProductSubscription.company_id == Company.id
    ).filter(
        CompanyProductSubscription.product_id == product_id
    ).offset(skip).limit(limit).all()
    
    total = db.query(func.count(CompanyProductSubscription.id)).filter(
        CompanyProductSubscription.product_id == product_id
    ).scalar()
    
    results = []
    for sub, company_name in subscriptions:
        budget = sub.monthly_claude_budget or 0
        used = sub.claude_used_this_month or 0
        results.append({
            "company_id": sub.company_id,
            "company_name": company_name,
            "monthly_budget": budget,
            "used_this_month": used,
            "remaining": budget - used,
            "usage_percent": round((used / budget * 100) if budget > 0 else 0, 1),
            "status": sub.status
        })
    
    # Sort by usage percent descending (highest users first)
    results.sort(key=lambda x: x["usage_percent"], reverse=True)
    
    return {
        "total": total,
        "companies": results
    }

