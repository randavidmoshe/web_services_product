# Form Pages Locator Service - Business Logic
# Location: web_services_product/api-server/services/form_pages_locator_service.py
#
# UPDATED: Added AI budget checking and BYOK mode support
# - Checks budget before allowing AI calls
# - Auto-resets budget every 30 days
# - BYOK mode (customer's own API key) has no limits

import os
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from models.database import (
    FormPageRoute, 
    CrawlSession, 
    Network, 
    Project, 
    ApiUsage,
    CompanyProductSubscription
)
from services.form_pages_ai_helper import FormPagesAIHelper


class AIBudgetExceededError(Exception):
    """Raised when company has exceeded their AI budget"""
    pass


class FormPagesLocatorService:
    """
    Service layer for Form Pages Locator feature.
    Handles AI operations for form discovery and stores results in database.
    """
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Initialize service with database session and optional API key.
        
        Args:
            db: SQLAlchemy database session
            api_key: Anthropic API key (or from environment/subscription)
        """
        self.db = db
        self.api_key = api_key
        self.ai_helper = None
        
        # Track created form names (to avoid duplicates within a session)
        self.created_form_names: List[str] = []
        
        # Current crawl session reference
        self.crawl_session_id: Optional[int] = None
        
        # UI verification flag
        self.ui_verification = True
        
        # Subscription reference (for budget tracking)
        self.subscription: Optional[CompanyProductSubscription] = None
        self.is_byok = False  # Bring Your Own Key - no limits
    
    def _check_and_reset_budget(self, subscription: CompanyProductSubscription) -> None:
        """
        Check if budget needs to be reset (30 days passed).
        
        Args:
            subscription: The subscription to check
        """
        if subscription.budget_reset_date:
            # Handle both date and datetime types
            reset_date = subscription.budget_reset_date
            if hasattr(reset_date, 'date'):
                reset_date = reset_date.date()
            
            if datetime.utcnow().date() >= reset_date:
                # Reset budget
                old_usage = subscription.claude_used_this_month
                subscription.claude_used_this_month = 0.0
                subscription.budget_reset_date = datetime.utcnow().date() + timedelta(days=30)
                self.db.commit()
                print(f"[FormPagesLocatorService] Budget reset for subscription {subscription.id}. Previous usage: ${old_usage:.2f}")
        else:
            # Set initial reset date if not set
            subscription.budget_reset_date = datetime.utcnow().date() + timedelta(days=30)
            self.db.commit()
            print(f"[FormPagesLocatorService] Set initial budget reset date for subscription {subscription.id}")
    
    def _check_budget(self, company_id: int, product_id: int) -> bool:
        """
        Check if company has remaining AI budget.
        
        Args:
            company_id: Company ID
            product_id: Product ID
            
        Returns:
            True if budget available or BYOK mode
            
        Raises:
            AIBudgetExceededError if budget exceeded
        """
        subscription = self.db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()
        
        if not subscription:
            print(f"[FormPagesLocatorService] No subscription found for company {company_id}, product {product_id}")
            return True  # No subscription = allow (shouldn't happen in production)
        
        self.subscription = subscription
        
        # BYOK mode - customer uses their own key, no limits
        if subscription.customer_claude_api_key:
            self.is_byok = True
            print(f"[FormPagesLocatorService] BYOK mode - no budget limits")
            return True
        
        # Check and reset budget if needed
        self._check_and_reset_budget(subscription)
        
        # Check if budget exceeded
        if subscription.claude_used_this_month >= subscription.monthly_claude_budget:
            days_until_reset = 0
            if subscription.budget_reset_date:
                delta = subscription.budget_reset_date - datetime.utcnow()
                days_until_reset = max(0, delta.days)
            
            raise AIBudgetExceededError(
                f"AI budget exceeded. Used: ${subscription.claude_used_this_month:.2f}, "
                f"Budget: ${subscription.monthly_claude_budget:.2f}. "
                f"Resets in {days_until_reset} days."
            )
        
        remaining = subscription.monthly_claude_budget - subscription.claude_used_this_month
        print(f"[FormPagesLocatorService] Budget check passed. Used: ${subscription.claude_used_this_month:.2f}, Remaining: ${remaining:.2f}")
        return True
    
    def _init_ai_helper(self, company_id: int, product_id: int) -> bool:
        """
        Initialize AI helper with API key from subscription or environment.
        Checks budget before initializing.
        
        Args:
            company_id: Company ID to look up subscription
            product_id: Product ID for the subscription
            
        Returns:
            True if AI helper initialized successfully
            
        Raises:
            AIBudgetExceededError if budget exceeded (only for non-BYOK)
        """
        # Check budget first (will set self.subscription and self.is_byok)
        self._check_budget(company_id, product_id)
        
        # Try to get API key from subscription first (BYOK mode)
        if not self.api_key and self.subscription:
            if self.subscription.customer_claude_api_key:
                self.api_key = self.subscription.customer_claude_api_key
                self.is_byok = True
        
        # Fall back to environment variable (our key)
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("[FormPagesLocatorService] No API key available - AI disabled")
            return False
        
        try:
            self.ai_helper = FormPagesAIHelper(api_key=self.api_key)
            print("[FormPagesLocatorService] AI Helper initialized")
            return True
        except Exception as e:
            print(f"[FormPagesLocatorService] Failed to initialize AI: {e}")
            return False
    
    # ========== CRAWL SESSION MANAGEMENT ==========
    
    def create_crawl_session(
        self,
        company_id: int,
        product_id: int,
        project_id: int,
        network_id: int,
        user_id: int
    ) -> CrawlSession:
        """
        Create a new crawl session for form discovery.
        
        Args:
            company_id: Company ID
            product_id: Product ID
            project_id: Project ID
            network_id: Network ID
            user_id: User ID who initiated the crawl
            
        Returns:
            Created CrawlSession object
        """
        session = CrawlSession(
            company_id=company_id,
            product_id=product_id,
            project_id=project_id,
            network_id=network_id,
            user_id=user_id,
            session_type='form_discovery',
            status='pending',
            pages_crawled=0,
            forms_found=0
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        self.crawl_session_id = session.id
        return session
    
    def update_crawl_session(
        self,
        session_id: int,
        status: Optional[str] = None,
        pages_crawled: Optional[int] = None,
        forms_found: Optional[int] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """
        Update crawl session status and counts.
        
        Args:
            session_id: CrawlSession ID
            status: New status
            pages_crawled: Number of pages crawled
            forms_found: Number of forms found
            error_message: Error message if failed
            error_code: Machine-readable error code (e.g., PAGE_NOT_FOUND, LOGIN_FAILED)
        """
        session = self.db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        
        if not session:
            return
        
        if status:
            session.status = status
            if status == 'running' and not session.started_at:
                session.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                session.completed_at = datetime.utcnow()
        
        if pages_crawled is not None:
            session.pages_crawled = pages_crawled
        
        if forms_found is not None:
            session.forms_found = forms_found
        
        if error_message:
            session.error_message = error_message
        
        if error_code:
            session.error_code = error_code
        
        self.db.commit()
    
    def get_crawl_session(self, session_id: int) -> Optional[CrawlSession]:
        """Get crawl session by ID"""
        return self.db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    
    # ========== FORM PAGE ROUTE MANAGEMENT ==========
    
    def save_form_route(
        self,
        company_id: int,
        product_id: int,
        project_id: int,
        network_id: int,
        crawl_session_id: int,
        form_name: str,
        url: str,
        login_url: str,
        username: str,
        navigation_steps: List[Dict[str, Any]],
        id_fields: List[str] = None,
        is_root: bool = True,
        verification_attempts: int = 1
    ) -> FormPageRoute:
        """
        Save a discovered form route to database.
        
        Args:
            company_id: Company ID
            product_id: Product ID
            project_id: Project ID
            network_id: Network ID
            crawl_session_id: CrawlSession ID
            form_name: AI-generated form name
            url: URL where form appears
            login_url: Login URL used
            username: Username used for login
            navigation_steps: Array of steps to reach the form
            id_fields: Array of reference field names
            is_root: Whether form has no parent dependencies
            verification_attempts: Number of verification attempts
            
        Returns:
            Created FormPageRoute object
        """
        # Check if form with same URL already exists (globally, not per network)
        existing = self.db.query(FormPageRoute).filter(
            FormPageRoute.url == url
        ).first()
        
        if existing:
            # Skip - form page with this URL already exists
            print(f"[FormPagesLocatorService] Form route already exists with URL: {url} - skipping")
            return existing
        
        # Create new route
        route = FormPageRoute(
            company_id=company_id,
            product_id=product_id,
            project_id=project_id,
            network_id=network_id,
            crawl_session_id=crawl_session_id,
            form_name=form_name,
            url=url,
            login_url=login_url,
            username=username,
            navigation_steps=navigation_steps,
            id_fields=id_fields or [],
            is_root=is_root,
            verification_attempts=verification_attempts,
            last_verified_at=datetime.utcnow()
        )
        
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        
        # Track the form name
        self.created_form_names.append(form_name)
        
        print(f"[FormPagesLocatorService] Saved form route: {form_name} ({url})")
        return route
    
    def get_form_routes(
        self,
        network_id: Optional[int] = None,
        project_id: Optional[int] = None,
        company_id: Optional[int] = None
    ) -> List[FormPageRoute]:
        """
        Get form routes with optional filters.
        
        Args:
            network_id: Filter by network
            project_id: Filter by project
            company_id: Filter by company
            
        Returns:
            List of FormPageRoute objects
        """
        query = self.db.query(FormPageRoute)
        
        if network_id:
            query = query.filter(FormPageRoute.network_id == network_id)
        if project_id:
            query = query.filter(FormPageRoute.project_id == project_id)
        if company_id:
            query = query.filter(FormPageRoute.company_id == company_id)
        
        return query.order_by(FormPageRoute.created_at.desc()).all()
    
    def build_hierarchy(self, network_id: int):
        """
        Build parent-child relationships for form routes in a network.
        Uses id_fields to determine relationships.
        
        Args:
            network_id: Network ID to build hierarchy for
        """
        routes = self.db.query(FormPageRoute).filter(
            FormPageRoute.network_id == network_id
        ).all()
        
        print(f"[FormPagesLocatorService] Building hierarchy for {len(routes)} routes")
        
        relationships_found = 0
        
        for route in routes:
            if not route.id_fields:
                continue
            
            # Look for parent forms based on id_fields
            for id_field in route.id_fields:
                # id_field might be like "employee_id" - look for "employee" form
                potential_parent = id_field.replace('_id', '').replace('Id', '').lower()
                
                for parent_route in routes:
                    if parent_route.id == route.id:
                        continue
                    
                    parent_name_normalized = parent_route.form_name.lower().replace('_', '')
                    potential_parent_base = potential_parent.replace('_', '')
                    
                    if potential_parent_base in parent_name_normalized or parent_name_normalized in potential_parent_base:
                        print(f"  🔗 {route.form_name} is child of {parent_route.form_name} (via {id_field})")
                        
                        # Set parent relationship
                        route.parent_form_route_id = parent_route.id
                        route.is_root = False
                        relationships_found += 1
                        break
        
        self.db.commit()
        print(f"[FormPagesLocatorService] Found {relationships_found} parent-child relationships")
    
    # ========== AI OPERATIONS ==========
    
    def generate_login_steps(
        self,
        page_html: str,
        screenshot_base64: str,
        username: str,
        password: str
    ) -> List[Dict[str, Any]]:
        """Generate login automation steps using AI"""
        if not self.ai_helper:
            print("[FormPagesLocatorService] AI not available")
            return []
        
        return self.ai_helper.generate_login_steps(page_html, screenshot_base64, username, password)
    
    def generate_logout_steps(
        self,
        page_html: str,
        screenshot_base64: str
    ) -> List[Dict[str, Any]]:
        """Generate logout automation steps using AI"""
        if not self.ai_helper:
            print("[FormPagesLocatorService] AI not available")
            return []
        
        return self.ai_helper.generate_logout_steps(page_html, screenshot_base64)
    
    def extract_form_name(self, context_data: Dict[str, Any]) -> str:
        """Extract semantic form name using AI"""
        if not self.ai_helper:
            return "unknown_form"
        
        return self.ai_helper.extract_form_name(context_data, self.created_form_names)
    
    def extract_parent_reference_fields(
        self,
        form_name: str,
        page_html: str,
        screenshot_base64: str = None
    ) -> List[Dict[str, Any]]:
        """Extract parent reference fields using AI"""
        if not self.ai_helper:
            return []
        
        return self.ai_helper.extract_parent_reference_fields(form_name, page_html, screenshot_base64)
    
    def verify_ui_defects(self, form_name: str, screenshot_base64: str) -> str:
        """Check for UI defects using AI Vision"""
        if not self.ai_helper or not self.ui_verification:
            return ""
        
        return self.ai_helper.verify_ui_defects(form_name, screenshot_base64)
    
    def is_submission_button(self, button_text: str) -> bool:
        """Determine if button is a submission button"""
        if not self.ai_helper:
            return False
        
        return self.ai_helper.is_submission_button(button_text)
    
    # ========== COST TRACKING ==========
    
    def get_ai_cost_summary(self) -> Dict[str, Any]:
        """Get AI usage cost summary"""
        if not self.ai_helper:
            return {
                "api_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "total_cost": 0.0
            }
        
        return self.ai_helper.get_cost_summary()
    
    def save_api_usage(
        self,
        company_id: int,
        product_id: int,
        user_id: int,
        crawl_session_id: int,
        operation_type: str = "form_discovery"
    ):
        """
        Save API usage to database for billing tracking.
        Skips tracking for BYOK mode.
        
        Args:
            company_id: Company ID
            product_id: Product ID
            user_id: User ID
            crawl_session_id: CrawlSession ID
            operation_type: Type of operation performed
        """
        if not self.ai_helper:
            return
        
        cost_summary = self.ai_helper.get_cost_summary()
        
        # Skip tracking if no usage
        if cost_summary["total_tokens"] == 0:
            return
        
        # Get subscription
        subscription = self.db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()
        
        # Skip tracking for BYOK mode
        if subscription and subscription.customer_claude_api_key:
            print(f"[FormPagesLocatorService] BYOK mode - skipping usage tracking")
            return
        
        # Log usage to api_usage table
        usage = ApiUsage(
            company_id=company_id,
            product_id=product_id,
            subscription_id=subscription.id if subscription else None,
            user_id=user_id,
            crawl_session_id=crawl_session_id,
            operation_type=operation_type,
            tokens_used=cost_summary["total_tokens"],
            api_cost=cost_summary["total_cost"]
        )
        
        self.db.add(usage)
        
        # Update subscription usage (accumulated total)
        if subscription:
            old_value = subscription.claude_used_this_month
            subscription.claude_used_this_month = old_value + cost_summary["total_cost"]
            print(f"[FormPagesLocatorService] Updating subscription {subscription.id}: {old_value} + {cost_summary['total_cost']} = {subscription.claude_used_this_month}")
            self.db.add(subscription)  # Explicitly mark as modified
        
        try:
            self.db.commit()
            print(f"[FormPagesLocatorService] Commit successful")
        except Exception as e:
            print(f"[FormPagesLocatorService] Commit failed: {e}")
            self.db.rollback()
            return
        
        print(f"[FormPagesLocatorService] Saved API usage: {cost_summary['total_tokens']} tokens, ${cost_summary['total_cost']:.4f}")
        if subscription:
            print(f"[FormPagesLocatorService] Total used this month: ${subscription.claude_used_this_month:.2f} / ${subscription.monthly_claude_budget:.2f}")
    
    # ========== AI USAGE QUERY (for dashboard) ==========
    
    @staticmethod
    def get_ai_usage_for_company(db: Session, company_id: int, product_id: int = 1) -> Dict[str, Any]:
        """
        Get AI usage information for dashboard display.
        
        Args:
            db: Database session
            company_id: Company ID
            product_id: Product ID (default 1)
            
        Returns:
            Dictionary with usage info for dashboard
        """
        subscription = db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()
        
        if not subscription:
            return {
                "used": 0,
                "budget": 200,
                "is_byok": False,
                "reset_date": None,
                "days_until_reset": None
            }
        
        # BYOK mode - no tracking
        if subscription.customer_claude_api_key:
            return {
                "used": None,
                "budget": None,
                "is_byok": True,
                "reset_date": None,
                "days_until_reset": None
            }
        
        # Calculate days until reset
        days_until_reset = None
        if subscription.budget_reset_date:
            # Handle both date and datetime types
            reset_date = subscription.budget_reset_date
            if hasattr(reset_date, 'date'):
                # It's a datetime, convert to date
                reset_date = reset_date.date()
            delta = reset_date - datetime.utcnow().date()
            days_until_reset = max(0, delta.days)
        
        return {
            "used": int(subscription.claude_used_this_month),  # Integer for display
            "budget": int(subscription.monthly_claude_budget),
            "is_byok": False,
            "reset_date": subscription.budget_reset_date.isoformat() if subscription.budget_reset_date else None,
            "days_until_reset": days_until_reset
        }
    
    # ========== UTILITY METHODS ==========
    
    def get_network_config(self, network_id: int) -> Optional[Dict[str, Any]]:
        """
        Get network configuration for crawler.
        
        Args:
            network_id: Network ID
            
        Returns:
            Dictionary with network config or None
        """
        network = self.db.query(Network).filter(Network.id == network_id).first()
        
        if not network:
            return None
        
        project = self.db.query(Project).filter(Project.id == network.project_id).first()
        
        return {
            "network_id": network.id,
            "network_name": network.name,
            "url": network.url,
            "login_username": network.login_username,
            "login_password": network.login_password,
            "project_id": network.project_id,
            "project_name": project.name if project else None,
            "company_id": network.company_id,
            "product_id": network.product_id
        }
    
    def prepare_crawl_task(
        self,
        network_id: int,
        user_id: int,
        max_depth: int = 20,
        max_form_pages: int = None,
        headless: bool = False,
        slow_mode: bool = True,
        ui_verification: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Prepare task parameters for form discovery crawl.
        
        Args:
            network_id: Network ID to crawl
            user_id: User ID initiating the crawl
            max_depth: Maximum navigation depth
            max_form_pages: Maximum forms to discover (None = unlimited)
            headless: Run browser in headless mode
            slow_mode: Add delays for observation
            ui_verification: Check for UI defects
            
        Returns:
            Dictionary with task parameters or None if network not found
            
        Raises:
            AIBudgetExceededError if budget exceeded
        """
        config = self.get_network_config(network_id)
        
        if not config:
            print(f"[FormPagesLocatorService] Network {network_id} not found")
            return None
        
        # Initialize AI helper (this checks budget)
        self._init_ai_helper(config["company_id"], config["product_id"])
        self.ui_verification = ui_verification
        
        # Create crawl session
        session = self.create_crawl_session(
            company_id=config["company_id"],
            product_id=config["product_id"],
            project_id=config["project_id"],
            network_id=network_id,
            user_id=user_id
        )
        
        return {
            "task_type": "discover_form_pages",
            "crawl_session_id": session.id,
            "network_url": config["url"],
            "login_url": config["url"],  # Assume same as network URL initially
            "login_username": config["login_username"],
            "login_password": config["login_password"],
            "project_name": config["project_name"],
            "company_id": config["company_id"],
            "product_id": config["product_id"],
            "project_id": config["project_id"],
            "network_id": network_id,
            "user_id": user_id,
            "max_depth": max_depth,
            "max_form_pages": max_form_pages,
            "headless": headless,
            "slow_mode": slow_mode,
            "ui_verification": ui_verification
        }
