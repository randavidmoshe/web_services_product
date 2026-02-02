from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.database import get_db
import redis
import os

router = APIRouter(prefix="/api/company", tags=["company"])


@router.get("/ai-usage")
async def get_ai_usage(
        company_id: int = Query(...),
        product_id: int = Query(default=1),
        db: Session = Depends(get_db)
):
    """
    Get AI usage for dashboard display.
    Returns used, budget, is_byok based on access model.
    """
    from services.ai_budget_service import get_budget_service

    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0
    )

    budget_service = get_budget_service(redis_client)
    return budget_service.get_dashboard_usage(db, company_id, product_id)