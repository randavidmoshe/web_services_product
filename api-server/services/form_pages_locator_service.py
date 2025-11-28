# Form Pages Locator Service - Business Logic
# Location: web_services_product/api-server/services/form_pages_locator_service.py

import os
from sqlalchemy.orm import Session
from datetime import datetime
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
    
    def _init_ai_helper(self, company_id: int, product_id: int) -> bool:
        """
        Initialize AI helper with API key from subscription or environment.
        
        Args:
            company_id: Company ID to look up subscription
            product_id: Product ID for the subscription
            
        Returns:
            True if AI helper initialized successfully
        """
        # Try to get API key from subscription first
        if not self.api_key:
            subscription = self.db.query(CompanyProductSubscription).filter(
                CompanyProductSubscription.company_id == company_id,
                CompanyProductSubscription.product_id == product_id
            ).first()
            
            if subscription and subscription.customer_claude_api_key:
                self.api_key = subscription.customer_claude_api_key
        
        # Fall back to environment variable
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
        error_message: Optional[str] = None
    ):
        """
        Update crawl session status and counts.
        
        Args:
            session_id: CrawlSession ID
            status: New status
            pages_crawled: Number of pages crawled
            forms_found: Number of forms found
            error_message: Error message if failed
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
        
        # Track form name
        if form_name not in self.created_form_names:
            self.created_form_names.append(form_name)
        
        print(f"[FormPagesLocatorService] Saved new form route: {form_name}")
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
        
        return query.order_by(FormPageRoute.form_name).all()
    
    def check_form_exists(self, network_id: int, form_url: str) -> bool:
        """
        Check if a form with this URL already exists.
        
        Args:
            network_id: Network ID
            form_url: URL of the form page to check
            
        Returns:
            True if form already exists, False otherwise
        """
        # Normalize URL for comparison (remove query params and hash)
        url_base = form_url.split('#')[0].split('?')[0]
        
        existing = self.db.query(FormPageRoute).filter(
            FormPageRoute.network_id == network_id
        ).all()
        
        for route in existing:
            existing_url_base = route.url.split('#')[0].split('?')[0]
            if url_base == existing_url_base:
                print(f"[FormPagesLocatorService] Form URL already exists: {url_base}")
                return True
        
        return False
    
    def build_hierarchy(self, network_id: int):
        """
        Build parent-child relationships based on id_fields.
        Called after all forms are discovered.
        
        Args:
            network_id: Network ID to build hierarchy for
        """
        print("[FormPagesLocatorService] Building parent-child hierarchy...")
        
        routes = self.db.query(FormPageRoute).filter(
            FormPageRoute.network_id == network_id
        ).all()
        
        relationships_found = 0
        
        for route in routes:
            id_fields = route.id_fields or []
            
            if not id_fields:
                continue
            
            for id_field in id_fields:
                # Extract potential parent name from ID field
                # e.g., "employee_id" -> "employee"
                potential_parent_base = (id_field
                                         .replace("_id", "")
                                         .replace("id", "")
                                         .replace("-", "")
                                         .replace("_", "")
                                         .strip()
                                         .lower())
                
                if not potential_parent_base:
                    continue
                
                # Find matching parent form
                for parent_route in routes:
                    if parent_route.id == route.id:
                        continue
                    
                    parent_name_normalized = parent_route.form_name.replace("_", "").replace("-", "").lower()
                    
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
        
        # Get subscription ID
        subscription = self.db.query(CompanyProductSubscription).filter(
            CompanyProductSubscription.company_id == company_id,
            CompanyProductSubscription.product_id == product_id
        ).first()
        
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
        
        # Update subscription usage
        if subscription:
            subscription.claude_used_this_month += cost_summary["total_cost"]
        
        self.db.commit()
        
        print(f"[FormPagesLocatorService] Saved API usage: {cost_summary['total_tokens']} tokens, ${cost_summary['total_cost']:.4f}")
    
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
        """
        config = self.get_network_config(network_id)
        
        if not config:
            print(f"[FormPagesLocatorService] Network {network_id} not found")
            return None
        
        # Initialize AI helper
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
