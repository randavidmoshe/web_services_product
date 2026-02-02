# ai_budget_service.py
# AI Token Budget Service - tracks usage and enforces limits
# Designed for high concurrency with hundreds of thousands of users

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, update
from enum import Enum

logger = logging.getLogger(__name__)

class AccessDeniedError(Exception):
    """Raised when AI access is denied (not a budget issue)"""
    def __init__(self, reason: str, code: str):
        self.reason = reason
        self.code = code
        super().__init__(reason)

class AIOperationType(str, Enum):
    """Types of AI operations for tracking"""
    # Form Mapper operations
    FORM_MAPPER_ANALYZE = "form_mapper_analyze"
    FORM_MAPPER_ALERT_RECOVERY = "form_mapper_alert_recovery"
    FORM_MAPPER_UI_VERIFY = "form_mapper_ui_verify"
    FORM_MAPPER_END_ASSIGN = "form_mapper_end_assign"
    FORM_MAPPER_REGENERATE = "form_mapper_regenerate"
    FORM_MAPPER_FIELD_ASSIST = "form_mapper_field_assist"
    # Forms Runner operations
    FORMS_RUNNER_ERROR_ANALYZE = "forms_runner_error_analyze"
    
    # Form Pages Locator operations
    FORM_PAGES_ANALYZE = "form_pages_analyze"
    FORM_PAGES_BUTTON_CHECK = "form_pages_button_check"


class BudgetExceededError(Exception):
    """Raised when company AI budget is exceeded"""
    def __init__(self, company_id: int, budget: float, used: float):
        self.company_id = company_id
        self.budget = budget
        self.used = used
        super().__init__(f"AI budget exceeded for company {company_id}: ${used:.2f}/${budget:.2f}")


class AIBudgetService:
    """
    Manages AI token budget checking and usage recording.
    
    Features:
    - Pre-call budget verification
    - Post-call usage recording
    - Atomic budget updates with row-level locking
    - Redis caching for high-frequency budget checks
    - Automatic budget reset handling
    
    Designed for high concurrency - uses optimistic locking and
    Redis caching to minimize database contention.
    """
    
    # Cost per 1M tokens (approximate, adjust as needed)
    COST_PER_1M_INPUT_TOKENS = 3.00   # Claude Sonnet input
    COST_PER_1M_OUTPUT_TOKENS = 15.00  # Claude Sonnet output
    
    # Cache TTL for budget info (seconds)
    BUDGET_CACHE_TTL = 60
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
    
    # ============================================================
    # BUDGET CHECKING (with Redis caching)
    # ============================================================
    
    def check_budget(
        self,
        db: Session,
        company_id: int,
        product_id: int,
        estimated_cost: float = 0.0
    ) -> Tuple[bool, float, float]:
        """
        Check if company has sufficient AI budget AND valid access.
        
        Uses Redis cache to reduce database load for high-frequency checks.
        
        Args:
            db: Database session
            company_id: Company ID
            product_id: Product ID (form_mapper, etc.)
            estimated_cost: Estimated cost of upcoming operation
            
        Returns:
            Tuple of (has_budget, remaining_budget, monthly_budget)
            
        Raises:
            AccessDeniedError if access denied (pending, expired, no key, etc.)
            BudgetExceededError if budget exceeded and estimated_cost > 0
        """
        from models.database import Company, CompanyProductSubscription

        # First check access status (cached)
        access_info = self._check_access_status(db, company_id, product_id)

        # BYOK mode - no budget limits
        if access_info.get("mode") == "byok":
            return (True, float('inf'), float('inf'))

        # Early Access - check daily budget
        if access_info.get("mode") == "early_access":
            return self._check_daily_budget(db, company_id, estimated_cost)

        # Legacy/default: check monthly subscription budget
        # Try Redis cache first
        cached = self._get_cached_budget(company_id, product_id)
        if cached:
            budget, used = cached
            remaining = budget - used
            
            if estimated_cost > 0 and remaining < estimated_cost:
                raise BudgetExceededError(company_id, budget, used)
            
            return (remaining > 0, remaining, budget)
        
        # Cache miss - query database

        subscription = db.query(CompanyProductSubscription).filter(
            and_(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id,
                CompanyProductSubscription.status.in_(["active", "trial"])
            )
        ).first()
        
        if not subscription:
            logger.warning(f"[AIBudget] No active subscription for company {company_id}, product {product_id}")
            return (False, 0.0, 0.0)
        
        # Check if budget needs reset
        self._check_budget_reset(db, subscription)
        
        budget = subscription.monthly_claude_budget or 0.0
        used = subscription.claude_used_this_month or 0.0
        remaining = budget - used
        
        # Cache the result
        self._cache_budget(company_id, product_id, budget, used)
        
        if estimated_cost > 0 and remaining < estimated_cost:
            raise BudgetExceededError(company_id, budget, used)
        
        return (remaining > 0, remaining, budget)
    
    def _check_budget_reset(self, db: Session, subscription) -> None:
        """Check and perform monthly budget reset if needed"""
        if not subscription.budget_reset_date:
            # Initialize reset date to next month
            subscription.budget_reset_date = datetime.utcnow().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=32)
            subscription.budget_reset_date = subscription.budget_reset_date.replace(day=1)
            db.commit()
            return
        
        # Convert to datetime for comparison if it's a date object
        reset_date = subscription.budget_reset_date
        if hasattr(reset_date, 'hour'):
            # It's already a datetime
            reset_datetime = reset_date
        else:
            # It's a date, convert to datetime at midnight
            reset_datetime = datetime.combine(reset_date, datetime.min.time())
        
        if datetime.utcnow() >= reset_datetime:
            # Reset budget
            subscription.claude_used_this_month = 0.0
            # Set next reset date (use reset_datetime which is guaranteed to be datetime)
            next_reset = reset_datetime + timedelta(days=32)
            subscription.budget_reset_date = next_reset.replace(day=1)
            db.commit()
            
            # Invalidate cache
            self._invalidate_budget_cache(subscription.company_id, subscription.product_id)
            
            logger.info(f"[AIBudget] Reset budget for company {subscription.company_id}")

    def _check_access_status(self, db: Session, company_id: int, product_id: int) -> dict:
        """
        Check company access status. Cached in Redis.

        Returns:
            dict with 'mode' (byok/early_access/legacy) and access info

        Raises:
            AccessDeniedError if access denied
        """
        from models.database import Company, CompanyProductSubscription
        from datetime import timedelta

        # Try cache first
        cache_key = f"ai_access:{company_id}"
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    import json
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"[AIBudget] Cache read error: {e}")

        # Query company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise AccessDeniedError("Company not found", "COMPANY_NOT_FOUND")

        # Check access_status
        access_status = getattr(company, 'access_status', None)
        access_model = getattr(company, 'access_model', None)

        # Legacy companies (no access_model set) - allow through to monthly budget check
        if not access_model:
            result = {"mode": "legacy", "allowed": True}
            self._cache_access(cache_key, result)
            return result

        # Check if access is active
        if access_status != 'active':
            if access_status == 'pending':
                raise AccessDeniedError(
                    "Your Early Access request is pending approval",
                    "ACCESS_PENDING"
                )
            else:
                raise AccessDeniedError(
                    "AI access is not available for your account",
                    "ACCESS_DENIED"
                )

        # BYOK mode
        if access_model == 'byok':
            subscription = db.query(CompanyProductSubscription).filter(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id
            ).first()

            if not subscription or not subscription.customer_claude_api_key:
                raise AccessDeniedError(
                    "No API key configured. Please add your API key in settings.",
                    "NO_API_KEY"
                )

            result = {"mode": "byok", "allowed": True}
            self._cache_access(cache_key, result)
            return result

        # Early Access mode
        if access_model == 'early_access':
            # Check trial expiration
            trial_start = getattr(company, 'trial_start_date', None)
            trial_days = getattr(company, 'trial_days_total', None) or 10

            if trial_start:
                trial_end = trial_start + timedelta(days=trial_days)
                if datetime.utcnow() > trial_end:
                    raise AccessDeniedError(
                        "Your trial has expired. Contact support or switch to BYOK.",
                        "TRIAL_EXPIRED"
                    )

            result = {
                "mode": "early_access",
                "allowed": True,
                "daily_budget": getattr(company, 'daily_ai_budget', None) or 10.0
            }
            self._cache_access(cache_key, result)
            return result

        # Unknown model - allow through to legacy check
        result = {"mode": "legacy", "allowed": True}
        self._cache_access(cache_key, result)
        return result

    def _cache_access(self, cache_key: str, result: dict) -> None:
        """Cache access check result"""
        if not self.redis:
            return
        try:
            import json
            self.redis.setex(cache_key, self.BUDGET_CACHE_TTL, json.dumps(result))
        except Exception as e:
            logger.warning(f"[AIBudget] Cache write error: {e}")

    def _check_daily_budget(
            self,
            db: Session,
            company_id: int,
            estimated_cost: float = 0.0
    ) -> Tuple[bool, float, float]:
        """Check daily budget with Redis caching"""

        # Try cache first
        cache_key = f"ai_daily_budget:{company_id}"
        if self.redis:
            try:
                cached = self.redis.hgetall(cache_key)
                if cached:
                    daily_budget = float(cached.get(b"budget", cached.get("budget", 10.0)))
                    used_today = float(cached.get(b"used", cached.get("used", 0.0)))
                    remaining = daily_budget - used_today

                    if estimated_cost > 0 and remaining < estimated_cost:
                        raise BudgetExceededError(company_id, daily_budget, used_today)

                    return (remaining > 0, remaining, daily_budget)
            except:
                pass

        # Cache miss - query DB
        from models.database import Company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return (False, 0.0, 0.0)

        # Reset if needed
        self._reset_daily_budget_if_needed(db, company)

        daily_budget = getattr(company, 'daily_ai_budget', None) or 10.0
        used_today = getattr(company, 'ai_used_today', None) or 0.0
        remaining = daily_budget - used_today

        # Cache it
        if self.redis:
            try:
                self.redis.hset(cache_key, mapping={"budget": daily_budget, "used": used_today})
                self.redis.expire(cache_key, self.BUDGET_CACHE_TTL)
            except:
                pass

        if estimated_cost > 0 and remaining < estimated_cost:
            raise BudgetExceededError(company_id, daily_budget, used_today)

        return (remaining > 0, remaining, daily_budget)

    def _reset_daily_budget_if_needed(self, db: Session, company) -> None:
        """Reset daily budget if 24 hours have passed"""
        now = datetime.utcnow()
        last_reset = getattr(company, 'last_usage_reset_date', None)

        if last_reset:
            hours_since_reset = (now - last_reset).total_seconds() / 3600
            if hours_since_reset >= 24:
                company.ai_used_today = 0.0
                company.last_usage_reset_date = now
                db.commit()
                logger.info(f"[AIBudget] Daily budget reset for company {company.id}")
                # Invalidate access cache
                if self.redis:
                    try:
                        self.redis.delete(f"ai_access:{company.id}")
                    except:
                        pass
        else:
            # First time - initialize
            company.last_usage_reset_date = now
            company.ai_used_today = 0.0
            db.commit()

    # ============================================================
    # USAGE RECORDING (with atomic updates)
    # ============================================================
    
    def record_usage(
        self,
        db: Session,
        company_id: int,
        product_id: int,
        user_id: int,
        operation_type: AIOperationType,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
        mapper_session_id: Optional[int] = None
    ) -> Dict:
        """
        Record AI usage and update budget atomically.
        
        Uses row-level locking to ensure accurate budget tracking
        under high concurrency.
        
        Args:
            db: Database session
            company_id: Company ID
            product_id: Product ID
            user_id: User who triggered the operation
            operation_type: Type of AI operation
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            session_id: Optional crawl/mapper session ID (string)
            mapper_session_id: Optional form mapper session ID (int)
            
        Returns:
            Dict with usage details and updated budget
        """
        from models.database import CompanyProductSubscription, ApiUsage
        
        # Calculate cost
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        try:
            # Get subscription with row lock for atomic update
            subscription = db.query(CompanyProductSubscription).filter(
                and_(
                    CompanyProductSubscription.company_id == company_id,
                    CompanyProductSubscription.product_id == product_id
                )
            ).with_for_update().first()
            
            if not subscription:
                logger.error(f"[AIBudget] No subscription for company {company_id}")
                return {"success": False, "error": "No subscription found"}

            # Check if Early Access - update company.ai_used_today instead
            from models.database import Company
            company = db.query(Company).filter(Company.id == company_id).first()

            if company and company.access_model == 'early_access':
                # Early Access - update daily budget
                old_usage = company.ai_used_today or 0.0
                company.ai_used_today = old_usage + cost
            else:
                # Legacy/Paid - update monthly budget
                old_usage = subscription.claude_used_this_month or 0.0
                subscription.claude_used_this_month = old_usage + cost
            
            # Create usage record
            usage_record = ApiUsage(
                company_id=company_id,
                product_id=product_id,
                subscription_id=subscription.id,
                user_id=user_id,
                crawl_session_id=None,  # Use mapper_session_id for form mapper
                operation_type=operation_type.value,
                tokens_used=total_tokens,
                api_cost=cost
            )
            db.add(usage_record)
            db.commit()
            
            # Invalidate cache
            self._invalidate_budget_cache(company_id, product_id)
            
            remaining = (subscription.monthly_claude_budget or 0.0) - subscription.claude_used_this_month
            
            logger.info(
                f"[AIBudget] Recorded {operation_type.value}: "
                f"tokens={total_tokens}, cost=${cost:.4f}, "
                f"remaining=${remaining:.2f} for company {company_id}"
            )
            
            return {
                "success": True,
                "tokens_used": total_tokens,
                "cost": cost,
                "remaining_budget": remaining,
                "usage_id": usage_record.id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"[AIBudget] Failed to record usage: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token counts"""
        input_cost = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT_TOKENS
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT_TOKENS
        return round(input_cost + output_cost, 6)

    def record_daily_usage(self, db: Session, company_id: int, cost: float) -> None:
        """Record daily usage with Redis atomic increment + async DB sync"""
        from models.database import Company

        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return

        access_model = getattr(company, 'access_model', None)
        if access_model != 'early_access':
            return

        # Atomic increment in Redis (fast)
        if self.redis:
            try:
                cache_key = f"ai_daily_budget:{company_id}"
                self.redis.hincrbyfloat(cache_key, "used", cost)
            except:
                pass

        # Also update DB (for persistence)
        current_used = getattr(company, 'ai_used_today', None) or 0.0
        company.ai_used_today = current_used + cost
        db.commit()

    # ============================================================
    # REDIS CACHING (for scalability)
    # ============================================================
    
    def _get_cache_key(self, company_id: int, product_id: int) -> str:
        return f"ai_budget:{company_id}:{product_id}"
    
    def _get_cached_budget(self, company_id: int, product_id: int) -> Optional[Tuple[float, float]]:
        """Get cached budget info (budget, used)"""
        if not self.redis:
            return None
        
        try:
            key = self._get_cache_key(company_id, product_id)
            data = self.redis.hgetall(key)
            
            if data:
                budget = float(data.get(b"budget", data.get("budget", 0)))
                used = float(data.get(b"used", data.get("used", 0)))
                return (budget, used)
        except Exception as e:
            logger.warning(f"[AIBudget] Cache read error: {e}")
        
        return None
    
    def _cache_budget(self, company_id: int, product_id: int, budget: float, used: float) -> None:
        """Cache budget info"""
        if not self.redis:
            return
        
        try:
            key = self._get_cache_key(company_id, product_id)
            self.redis.hset(key, mapping={"budget": budget, "used": used})
            self.redis.expire(key, self.BUDGET_CACHE_TTL)
        except Exception as e:
            logger.warning(f"[AIBudget] Cache write error: {e}")
    
    def _invalidate_budget_cache(self, company_id: int, product_id: int) -> None:
        """Invalidate cached budget after update"""
        if not self.redis:
            return
        
        try:
            key = self._get_cache_key(company_id, product_id)
            self.redis.delete(key)
        except Exception as e:
            logger.warning(f"[AIBudget] Cache invalidation error: {e}")
    
    # ============================================================
    # BATCH OPERATIONS (for efficiency)
    # ============================================================
    
    def record_usage_batch(
        self,
        db: Session,
        usages: list[Dict]
    ) -> Dict:
        """
        Record multiple usage entries in a single transaction.
        More efficient for high-volume scenarios.
        
        Args:
            db: Database session
            usages: List of usage dicts with keys:
                company_id, product_id, user_id, operation_type,
                input_tokens, output_tokens
                
        Returns:
            Dict with batch results
        """
        from models.database import CompanyProductSubscription, ApiUsage
        
        if not usages:
            return {"success": True, "recorded": 0}
        
        try:
            # Group by company+product for efficient updates
            grouped = {}
            for u in usages:
                key = (u["company_id"], u["product_id"])
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(u)
            
            total_recorded = 0
            
            for (company_id, product_id), company_usages in grouped.items():
                # Get subscription with lock
                subscription = db.query(CompanyProductSubscription).filter(
                    and_(
                        CompanyProductSubscription.company_id == company_id,
                        CompanyProductSubscription.product_id == product_id
                    )
                ).with_for_update().first()
                
                if not subscription:
                    continue
                
                total_cost = 0.0
                records = []
                
                for u in company_usages:
                    cost = self._calculate_cost(u["input_tokens"], u["output_tokens"])
                    total_cost += cost
                    
                    records.append(ApiUsage(
                        company_id=company_id,
                        product_id=product_id,
                        subscription_id=subscription.id,
                        user_id=u["user_id"],
                        operation_type=u["operation_type"].value if isinstance(u["operation_type"], AIOperationType) else u["operation_type"],
                        tokens_used=u["input_tokens"] + u["output_tokens"],
                        api_cost=cost
                    ))
                
                # Bulk insert
                db.bulk_save_objects(records)
                
                # Update subscription
                subscription.claude_used_this_month = (subscription.claude_used_this_month or 0.0) + total_cost
                
                total_recorded += len(records)
                
                # Invalidate cache
                self._invalidate_budget_cache(company_id, product_id)
            
            db.commit()
            
            return {"success": True, "recorded": total_recorded}
            
        except Exception as e:
            db.rollback()
            logger.error(f"[AIBudget] Batch record failed: {e}")
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # REPORTING (for admin)
    # ============================================================
    
    def get_company_usage_summary(
        self,
        db: Session,
        company_id: int,
        product_id: int
    ) -> Dict:
        """Get usage summary for a company"""
        from models.database import CompanyProductSubscription, ApiUsage
        from sqlalchemy import func
        
        subscription = db.query(CompanyProductSubscription).filter(
            and_(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id
            )
        ).first()
        
        if not subscription:
            return {"error": "No subscription found"}
        
        # Convert budget_reset_date to datetime if it's a date
        reset_date = subscription.budget_reset_date
        if reset_date:
            if hasattr(reset_date, 'hour'):
                reset_datetime = reset_date
            else:
                reset_datetime = datetime.combine(reset_date, datetime.min.time())
            filter_date = reset_datetime - timedelta(days=32)
        else:
            filter_date = datetime.utcnow() - timedelta(days=32)
        
        # Get usage breakdown by operation type
        breakdown = db.query(
            ApiUsage.operation_type,
            func.count(ApiUsage.id).label("count"),
            func.sum(ApiUsage.tokens_used).label("total_tokens"),
            func.sum(ApiUsage.api_cost).label("total_cost")
        ).filter(
            and_(
                ApiUsage.company_id == company_id,
                ApiUsage.product_id == product_id,
                ApiUsage.created_at >= filter_date
            )
        ).group_by(ApiUsage.operation_type).all()
        
        return {
            "company_id": company_id,
            "monthly_budget": subscription.monthly_claude_budget,
            "used_this_month": subscription.claude_used_this_month,
            "remaining": (subscription.monthly_claude_budget or 0) - (subscription.claude_used_this_month or 0),
            "budget_reset_date": subscription.budget_reset_date.isoformat() if subscription.budget_reset_date else None,
            "breakdown": [
                {
                    "operation_type": row.operation_type,
                    "count": row.count,
                    "total_tokens": row.total_tokens,
                    "total_cost": float(row.total_cost) if row.total_cost else 0
                }
                for row in breakdown
            ]
        }

    def get_dashboard_usage(self, db: Session, company_id: int, product_id: int = 1) -> dict:
        """
        Get AI usage for dashboard display.
        Handles BYOK, Early Access, and Legacy modes.
        Uses Redis caching for scalability.
        """
        from models.database import Company, CompanyProductSubscription

        # Check access status (cached)
        try:
            access_info = self._check_access_status(db, company_id, product_id)
        except AccessDeniedError:
            return {"used": 0, "budget": 0, "is_byok": False}

        # BYOK - no tracking
        if access_info.get("mode") == "byok":
            return {"used": None, "budget": None, "is_byok": True}

        # Early Access - daily budget
        if access_info.get("mode") == "early_access":
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                self._reset_daily_budget_if_needed(db, company)
                return {
                    "used": int(company.ai_used_today or 0),
                    "budget": int(company.daily_ai_budget or 10),
                    "is_byok": False
                }

        # Legacy - monthly budget
        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()

        if subscription:
            return {
                "used": int(subscription.claude_used_this_month or 0),
                "budget": int(subscription.monthly_claude_budget or 0),
                "is_byok": False
            }

        return {"used": 0, "budget": 0, "is_byok": False}

# Export error classes for use by callers
__all__ = ['AIBudgetService', 'BudgetExceededError', 'AccessDeniedError', 'AIOperationType', 'get_budget_service']

# Singleton instance for convenience
_budget_service: Optional[AIBudgetService] = None

def get_budget_service(redis_client=None) -> AIBudgetService:
    """Get or create budget service singleton"""
    global _budget_service
    if _budget_service is None:
        _budget_service = AIBudgetService(redis_client)
    return _budget_service
