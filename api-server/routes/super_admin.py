from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.database import get_db, Company, User, SuperAdmin, CompanyProductSubscription
from utils.auth_helpers import get_current_super_admin, log_super_admin_action
from services.email_service import notify_product_owner

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


class ApproveAccessRequest(BaseModel):
    company_id: int
    daily_ai_budget: Optional[float] = None
    trial_days_total: Optional[int] = None


class RejectAccessRequest(BaseModel):
    company_id: int
    reason: Optional[str] = None


class UpdateLimitsRequest(BaseModel):
    company_id: int
    daily_ai_budget: Optional[float] = None
    trial_days_total: Optional[int] = None


@router.get("/pending-access")
async def get_pending_access_requests(
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Get all companies with pending Early Access requests."""
    admin = get_current_super_admin(authorization, db)

    pending_companies = db.query(Company).filter(
        Company.access_model == 'early_access',
        Company.access_status == 'pending'
    ).all()

    result = []
    for company in pending_companies:
        admin_user = db.query(User).filter(
            User.company_id == company.id,
            User.role == 'admin'
        ).first()

        result.append({
            "company_id": company.id,
            "company_name": company.name,
            "billing_email": company.billing_email,
            "admin_name": admin_user.name if admin_user else None,
            "admin_email": admin_user.email if admin_user else None,
            "account_category": company.account_category,
            "created_at": company.created_at.isoformat() if company.created_at else None,
            "daily_ai_budget": company.daily_ai_budget or 10.0,
            "trial_days_total": company.trial_days_total or 10
        })

    return {"pending": result, "count": len(result)}


@router.get("/all-companies")
async def get_all_companies(
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Get all companies with their access status."""
    admin = get_current_super_admin(authorization, db)

    companies = db.query(Company).order_by(Company.created_at.desc()).all()

    result = []
    for company in companies:
        admin_user = db.query(User).filter(
            User.company_id == company.id,
            User.role == 'admin'
        ).first()

        result.append({
            "company_id": company.id,
            "company_name": company.name,
            "billing_email": company.billing_email,
            "admin_name": admin_user.name if admin_user else None,
            "admin_email": admin_user.email if admin_user else None,
            "account_category": company.account_category,
            "access_model": company.access_model,
            "access_status": company.access_status,
            "onboarding_completed": company.onboarding_completed,
            "daily_ai_budget": company.daily_ai_budget,
            "trial_days_total": company.trial_days_total,
            "trial_start_date": company.trial_start_date.isoformat() if company.trial_start_date else None,
            "ai_used_today": company.ai_used_today,
            "created_at": company.created_at.isoformat() if company.created_at else None
        })

    return {"companies": result, "count": len(result)}


@router.post("/approve-access")
async def approve_access(
        data: ApproveAccessRequest,
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Approve Early Access for a company."""
    admin = get_current_super_admin(authorization, db)

    company = db.query(Company).filter(Company.id == data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.access_status == 'active':
        raise HTTPException(status_code=400, detail="Already approved")

    company.access_status = 'active'
    company.trial_start_date = datetime.utcnow()
    company.ai_used_today = 0.0
    company.last_usage_reset_date = datetime.utcnow()

    # Override limits if provided
    if data.daily_ai_budget is not None:
        company.daily_ai_budget = data.daily_ai_budget
    if data.trial_days_total is not None:
        company.trial_days_total = data.trial_days_total

    # If onboarding category is set, mark onboarding complete
    if company.account_category:
        company.onboarding_completed = True

    # Update subscription status
    subscription = db.query(CompanyProductSubscription).filter(
        CompanyProductSubscription.company_id == company.id
    ).first()
    if subscription:
        subscription.status = 'active'

    db.commit()

    # Send approval notification email
    admin_user = db.query(User).filter(
        User.company_id == company.id,
        User.role == 'admin'
    ).first()

    if admin_user and admin_user.email:
        from services.email_service import send_early_access_approved_email_queued
        send_early_access_approved_email_queued(
            to_email=admin_user.email,
            to_name=admin_user.name or "User",
            company_name=company.name,
            daily_budget=company.daily_ai_budget,
            trial_days=company.trial_days_total
        )

    # Audit log
    log_super_admin_action(
        db=db,
        admin_id=admin.id,
        action="approve_access",
        target_company_id=company.id,
        details={
            "daily_ai_budget": company.daily_ai_budget,
            "trial_days_total": company.trial_days_total
        },
        ip_address=request.client.host if request.client else None
    )

    # Notify product owner
    notify_product_owner(
        action="approve_access",
        details={
            "company": company.name,
            "company_id": company.id,
            "daily_budget": f"${company.daily_ai_budget:.2f}",
            "trial_days": company.trial_days_total
        },
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "success",
        "message": f"Approved access for {company.name}",
        "company_id": company.id,
        "trial_start_date": company.trial_start_date.isoformat(),
        "daily_ai_budget": company.daily_ai_budget,
        "trial_days_total": company.trial_days_total
    }


@router.post("/reject-access")
async def reject_access(
        data: RejectAccessRequest,
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Reject Early Access for a company."""
    admin = get_current_super_admin(authorization, db)

    company = db.query(Company).filter(Company.id == data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.access_status = 'rejected'
    db.commit()

    # Audit log
    log_super_admin_action(
        db=db,
        admin_id=admin.id,
        action="reject_access",
        target_company_id=company.id,
        details={"reason": data.reason} if data.reason else None,
        ip_address=request.client.host if request.client else None
    )

    # Notify product owner
    notify_product_owner(
        action="reject_access",
        details={
            "company": company.name,
            "company_id": company.id,
            "reason": data.reason or "No reason provided"
        },
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "success",
        "message": f"Rejected access for {company.name}",
        "company_id": company.id
    }


@router.patch("/company-limits")
async def update_company_limits(
        data: UpdateLimitsRequest,
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Update daily budget or trial days for a company."""
    admin = get_current_super_admin(authorization, db)

    company = db.query(Company).filter(Company.id == data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    old_values = {
        "daily_ai_budget": company.daily_ai_budget,
        "trial_days_total": company.trial_days_total
    }

    if data.daily_ai_budget is not None:
        company.daily_ai_budget = data.daily_ai_budget
    if data.trial_days_total is not None:
        company.trial_days_total = data.trial_days_total

    db.commit()

    # Audit log
    log_super_admin_action(
        db=db,
        admin_id=admin.id,
        action="update_limits",
        target_company_id=company.id,
        details={
            "old": old_values,
            "new": {
                "daily_ai_budget": company.daily_ai_budget,
                "trial_days_total": company.trial_days_total
            }
        },
        ip_address=request.client.host if request.client else None
    )

    # Notify product owner
    notify_product_owner(
        action="update_limits",
        details={
            "company": company.name,
            "company_id": company.id,
            "old_budget": f"${old_values['daily_ai_budget']:.2f}" if old_values['daily_ai_budget'] else "N/A",
            "new_budget": f"${company.daily_ai_budget:.2f}" if company.daily_ai_budget else "N/A",
            "old_trial_days": old_values['trial_days_total'],
            "new_trial_days": company.trial_days_total
        },
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "success",
        "company_id": company.id,
        "daily_ai_budget": company.daily_ai_budget,
        "trial_days_total": company.trial_days_total
    }


@router.post("/disable-company")
async def disable_company(
        company_id: int,
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Disable a company (set access_status to rejected)."""
    admin = get_current_super_admin(authorization, db)

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.access_status = 'rejected'
    db.commit()

    # Audit log
    log_super_admin_action(
        db=db,
        admin_id=admin.id,
        action="disable_company",
        target_company_id=company.id,
        ip_address=request.client.host if request.client else None
    )

    # Notify product owner
    notify_product_owner(
        action="disable_company",
        details={"company": company.name, "company_id": company.id},
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "success",
        "message": f"Disabled {company.name}"
    }


@router.post("/enable-company")
async def enable_company(
        company_id: int,
        request: Request,
        authorization: str = Header(...),
        db: Session = Depends(get_db)
):
    """Re-enable a disabled company."""
    admin = get_current_super_admin(authorization, db)

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.access_status = 'active'

    # Reset trial if needed
    if not company.trial_start_date:
        company.trial_start_date = datetime.utcnow()

    db.commit()

    # Send notification email if this is an Early Access company
    if company.access_model == 'early_access':
        admin_user = db.query(User).filter(
            User.company_id == company.id,
            User.role == 'admin'
        ).first()

        if admin_user and admin_user.email:
            from services.email_service import send_early_access_approved_email_queued
            send_early_access_approved_email_queued(
                to_email=admin_user.email,
                to_name=admin_user.name or "User",
                company_name=company.name,
                daily_budget=company.daily_ai_budget or 10.0,
                trial_days=company.trial_days_total or 10
            )

    # Audit log
    log_super_admin_action(
        db=db,
        admin_id=admin.id,
        action="enable_company",
        target_company_id=company.id,
        ip_address=request.client.host if request.client else None
    )

    # Notify product owner
    notify_product_owner(
        action="enable_company",
        details={"company": company.name, "company_id": company.id},
        ip_address=request.client.host if request.client else None
    )

    return {
        "status": "success",
        "message": f"Enabled {company.name}"
    }


@router.get("/audit-logs")
async def get_audit_logs(
        request: Request,
        authorization: str = Header(...),
        limit: int = 50,
        db: Session = Depends(get_db)
):
    """Get super admin audit logs."""
    from models.database import SuperAdminAuditLog

    admin = get_current_super_admin(authorization, db)

    logs = db.query(SuperAdminAuditLog).order_by(
        SuperAdminAuditLog.created_at.desc()
    ).limit(limit).all()

    return {
        "logs": [
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "action": log.action,
                "target_company_id": log.target_company_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "count": len(logs)
    }