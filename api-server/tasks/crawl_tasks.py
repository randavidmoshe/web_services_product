from celery_app import celery
from datetime import datetime
from models.database import SessionLocal, CrawlSession, FormPageRoute, ApiUsage
import os

@celery.task(bind=True)
def discover_form_pages_task(self, session_id: int, network_url: str, company_id: int, product_id: int, user_id: int):
    """
    Background task to discover form pages
    This runs in a Celery worker, not blocking the API server
    """
    db = SessionLocal()
    
    try:
        # Update session status to running
        session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        session.status = "running"
        session.started_at = datetime.utcnow()
        db.commit()
        
        # Update task progress
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Starting crawler...'})
        
        # ============================================
        # TODO: YOUR PART 1 CODE GOES HERE
        # ============================================
        # This is where you'll call your form discovery logic
        # Example:
        # from services.part1.discovery import discover_forms
        # results = discover_forms(network_url)
        
        # MOCK IMPLEMENTATION (replace with your code)
        import time
        time.sleep(2)  # Simulate work
        
        # Mock results
        mock_results = [
            {"url": f"{network_url}/contact", "title": "Contact Form", "forms_count": 1},
            {"url": f"{network_url}/signup", "title": "Sign Up", "forms_count": 1},
            {"url": f"{network_url}/checkout", "title": "Checkout", "forms_count": 2},
        ]
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Analyzing forms...'})
        
        # Save results to database
        for result in mock_results:
            form_page = FormPageDiscovered(
                company_id=company_id,
                product_id=product_id,
                crawl_session_id=session_id,
                url=result["url"],
                page_title=result["title"],
                forms_count=result["forms_count"]
            )
            db.add(form_page)
        
        # Update session
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        session.pages_crawled = len(mock_results)
        session.forms_found = sum(r["forms_count"] for r in mock_results)
        
        # Track API usage (mock - replace with actual token count)
        api_usage = ApiUsage(
            company_id=company_id,
            product_id=product_id,
            subscription_id=1,  # TODO: Get from session
            user_id=user_id,
            crawl_session_id=session_id,
            operation_type="discover_form_pages",
            tokens_used=1500,  # Mock value
            api_cost=0.03  # Mock value
        )
        db.add(api_usage)
        
        db.commit()
        
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Complete!'})
        
        return {
            'status': 'completed',
            'pages_found': len(mock_results),
            'forms_found': session.forms_found
        }
        
    except Exception as e:
        # Handle errors
        session.status = "failed"
        session.error_message = str(e)
        session.completed_at = datetime.utcnow()
        db.commit()
        
        raise
        
    finally:
        db.close()


@celery.task(bind=True)
def analyze_form_details_task(self, form_page_id: int, company_id: int, product_id: int, user_id: int):
    """
    Background task to analyze form details (Part 2)
    """
    db = SessionLocal()
    
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': 'Analyzing form...'})
        
        # ============================================
        # TODO: YOUR PART 2 CODE GOES HERE
        # ============================================
        # This is where you'll call your form analysis logic
        
        # MOCK IMPLEMENTATION
        import time
        time.sleep(3)  # Simulate work
        
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Complete!'})
        
        return {'status': 'completed', 'fields_found': 5}
        
    except Exception as e:
        raise
    finally:
        db.close()


@celery.task
def check_budget_task(company_id: int, product_id: int, subscription_id: int):
    """
    Task to check if company has budget remaining
    Returns True if budget available, False otherwise
    """
    db = SessionLocal()
    
    try:
        from models.database import CompanyProductSubscription
        
        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            return False
        
        # Check if budget exhausted
        if subscription.claude_used_this_month >= subscription.monthly_claude_budget:
            return False
        
        return True
        
    finally:
        db.close()


@celery.task
def reset_monthly_budgets_task():
    """
    Cron task to reset monthly budgets
    Run this on the 1st of each month
    """
    db = SessionLocal()
    
    try:
        from models.database import CompanyProductSubscription
        from datetime import date
        
        # Reset all subscriptions
        subscriptions = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.budget_reset_date <= date.today()
        ).all()
        
        for sub in subscriptions:
            sub.claude_used_this_month = 0.0
            # Set next reset date to next month
            from dateutil.relativedelta import relativedelta
            sub.budget_reset_date = date.today() + relativedelta(months=1)
        
        db.commit()
        
        return f"Reset {len(subscriptions)} budgets"
        
    finally:
        db.close()
