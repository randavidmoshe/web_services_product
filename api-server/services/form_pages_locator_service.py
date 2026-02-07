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
from services.session_logger import get_session_logger, ActivityType
from services.encryption_service import get_decrypted_api_key, decrypt_credential

from services.s3_storage import generate_presigned_put_url

from models.database import (
    FormPageRoute, 
    CrawlSession, 
    Network, 
    Project, 
    ApiUsage,
    CompanyProductSubscription,
    ProjectFormHierarchy
)
from services.form_pages_ai_helper import FormPagesAIHelper
from services.ai_budget_service import get_budget_service, BudgetExceededError, AccessDeniedError




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

    def _get_logger(self, session_id: str = None, company_id: int = None):
        """Get structured logger for discovery operations"""
        return get_session_logger(
            db_session=None,
            activity_type=ActivityType.DISCOVERY.value,
            session_id=session_id,
            company_id=company_id
        )


    
    def _check_budget(self, company_id: int, product_id: int) -> bool:
        """
        Check if company has remaining AI budget.
        
        Args:
            company_id: Company ID
            product_id: Product ID
            
        Returns:
            True if budget available or BYOK mode
            
        Raises:
            BudgetExceededError if budget exceeded
            AccessDeniedError if access denied (pending, expired, etc.)
        """
        redis_client = None
        try:
            import redis
            import os
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=0
            )
        except:
            pass

        budget_service = get_budget_service(redis_client)
        has_budget, remaining, total = budget_service.check_budget(
            self.db, company_id, product_id
        )

        if not has_budget:
            raise BudgetExceededError(company_id, total, total - remaining)

        # Check if BYOK (remaining is infinity)
        if remaining == float('inf'):
            self.is_byok = True
            print(f"[FormPagesLocatorService] BYOK mode - no budget limits")
        else:
            print(f"[FormPagesLocatorService] Budget check passed. Remaining: ${remaining:.2f}")

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

        # Check budget first
        self._check_budget(company_id, product_id)

        # Load subscription to check for BYOK key
        if not self.api_key:
            self.subscription = self.db.query(CompanyProductSubscription).filter(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id
            ).first()

            if self.subscription and self.subscription.customer_claude_api_key:
                # Decrypt the API key (uses Redis cache for performance)
                self.api_key = get_decrypted_api_key(
                    company_id,
                    self.subscription.customer_claude_api_key
                )
                self.is_byok = True
        
        # Fall back to environment variable (our key)
        if not self.api_key:
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            print("[FormPagesLocatorService] No API key available - AI disabled")
            log = self._get_logger()
            log.warning("No API key available - AI disabled", category="discovery")
            return False
        
        try:
            self.ai_helper = FormPagesAIHelper(api_key=self.api_key)
            print("[FormPagesLocatorService] AI Helper initialized")
            log = self._get_logger()
            log.info("AI Helper initialized", category="discovery")
            return True
        except Exception as e:
            print(f"[FormPagesLocatorService] Failed to initialize AI: {e}")
            log = self._get_logger()
            log.error(f"Failed to initialize AI: {e}", category="error")
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
        parent_fields: List[Dict[str, Any]] = None,
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
            parent_fields: Full parent reference field objects from AI
            is_root: Whether form has no parent dependencies
            verification_attempts: Number of verification attempts
            
        Returns:
            Created FormPageRoute object
        """
        # Check if form with same URL already exists (globally, not per network)
        existing = self.db.query(FormPageRoute).filter(
            FormPageRoute.url == url,
            FormPageRoute.project_id == project_id
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
            parent_fields=parent_fields or [],
            is_root=is_root,
            verification_attempts=verification_attempts,
            last_verified_at=datetime.utcnow()
        )
        
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        
        # Increment forms_found in crawl session
        if crawl_session_id:
            session = self.db.query(CrawlSession).filter(CrawlSession.id == crawl_session_id).first()
            if session:
                session.forms_found = (session.forms_found or 0) + 1
                self.db.commit()
        
        # Track the form name
        self.created_form_names.append(form_name)

        print(f"[FormPagesLocatorService] Saved form route: {form_name} ({url})")
        log = self._get_logger(company_id=company_id)
        log.info(f"Saved form route: {form_name}", category="discovery", form_name=form_name, url=url)
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
        Build parent-child relationships for form pages at project level.
        Uses AI to intelligently match parent reference fields to forms.
        Saves to ProjectFormHierarchy table.

        Args:
            network_id: Network ID (used to get project_id and forms)
        """
        # Get network to find project_id
        network = self.db.query(Network).filter(Network.id == network_id).first()
        if not network:
            print("[FormPagesLocatorService] Network not found")
            return

        project_id = network.project_id

        # Get ALL form routes for this PROJECT (across all networks)
        routes = self.db.query(FormPageRoute).filter(
            FormPageRoute.project_id == project_id
        ).all()

        print(f"[FormPagesLocatorService] Building hierarchy for {len(routes)} routes in project {project_id}")

        if not routes:
            print("[FormPagesLocatorService] No routes found")
            return

        # Gather all forms with their parent fields (include network_id for context)
        forms_data = []
        for route in routes:
            forms_data.append({
                "form_id": route.id,
                "form_name": route.form_name,
                "network_id": route.network_id,
                "parent_fields": route.parent_fields or []
            })

        print(f"[FormPagesLocatorService] Sending {len(forms_data)} forms to AI for hierarchy")
        log = self._get_logger()
        log.ai_call("build_hierarchy", prompt_size=len(str(forms_data)))

        # Call AI to build hierarchy
        if not self.ai_helper:
            print("[FormPagesLocatorService] AI not available, skipping hierarchy")
            return

        hierarchy = self.ai_helper.build_form_hierarchy(forms_data)

        if not hierarchy:
            print("[FormPagesLocatorService] AI returned no hierarchy")
            return

        # Clear existing hierarchy for this project
        self.db.query(ProjectFormHierarchy).filter(
            ProjectFormHierarchy.project_id == project_id
        ).delete()

        # Build lookup for form names
        route_by_id = {r.id: r for r in routes}

        # Save new hierarchy to ProjectFormHierarchy table
        relationships_found = 0
        for item in hierarchy:
            form_id = item.get("form_id")
            parent_form_id = item.get("parent_form_id")

            if form_id not in route_by_id:
                continue

            form_name = route_by_id[form_id].form_name
            parent_form_name = route_by_id[
                parent_form_id].form_name if parent_form_id and parent_form_id in route_by_id else None

            hierarchy_entry = ProjectFormHierarchy(
                project_id=project_id,
                form_id=form_id,
                form_name=form_name,
                parent_form_id=parent_form_id if parent_form_id and parent_form_id in route_by_id else None,
                parent_form_name=parent_form_name
            )
            self.db.add(hierarchy_entry)

            if parent_form_name:
                relationships_found += 1
                print(f"  🔗 {form_name} (id={form_id}) is child of {parent_form_name} (id={parent_form_id})")
            else:
                print(f"  📍 {form_name} (id={form_id}) is root form")

        self.db.commit()
        print(f"[FormPagesLocatorService] Saved hierarchy: {relationships_found} parent-child relationships")
        log = self._get_logger()
        log.ai_response("build_hierarchy", success=True)
        log.info(f"Saved hierarchy: {relationships_found} relationships", category="discovery",
                 relationships_count=relationships_found)
    
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
    
    def is_submission_button(self, button_text: str, screenshot_base64: str = None) -> bool:
        """Determine if button is a submission button"""
        if not self.ai_helper:
            return False
        
        return self.ai_helper.is_submission_button(button_text, screenshot_base64)
    
    def get_navigation_clickables(self, screenshot_base64: str) -> List[str]:
        """Ask AI to identify navigation clickables from screenshot"""
        if not self.ai_helper:
            return []
        
        return self.ai_helper.get_navigation_clickables(screenshot_base64)
    
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

        print(
            f"[FormPagesLocatorService] Saved API usage: {cost_summary['total_tokens']} tokens, ${cost_summary['total_cost']:.4f}")
        log = self._get_logger(company_id=company_id)
        log.info(f"API usage: {cost_summary['total_tokens']} tokens, ${cost_summary['total_cost']:.4f}",
                 category="budget", tokens=cost_summary['total_tokens'], cost=cost_summary['total_cost'])

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
        project_type = project.project_type if project else 'enterprise'
        
        return {
            "network_id": network.id,
            "network_name": network.name,
            "url": network.url,
            "login_username": decrypt_credential(network.login_username, network.company_id, network.id, "username") if network.login_username else None,
            "login_password": decrypt_credential(network.login_password, network.company_id, network.id, "password") if network.login_password else None,
            "project_id": network.project_id,
            "project_name": project.name if project else None,
            "company_id": network.company_id,
            "product_id": network.product_id,
            "project_type": project_type
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

        # Generate pre-signed URLs for uploads (all logs go to S3)
        logs_s3_key = f"logs/{config['company_id']}/{config['project_id']}/discovery_{session.id}.json"
        logs_url = generate_presigned_put_url(
            s3_key=logs_s3_key,
            content_type='application/json',
            expiration=7200  # 2 hours
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
            "skip_form_crawl": config.get("project_type") == "dynamic_content",
            "user_id": user_id,
            "max_depth": max_depth,
            "max_form_pages": max_form_pages,
            "headless": headless,
            "slow_mode": slow_mode,
            "ui_verification": ui_verification,
            "upload_urls": {
                "logs": logs_url,
                "logs_s3_key": logs_s3_key
            }
        }
