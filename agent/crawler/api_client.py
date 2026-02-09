# Form Pages API Client
# Location: web_services_product/agent/crawler/api_client.py
#
# HTTP client that replaces direct server.method() calls
# Agent crawler uses this to communicate with API server
#
# Security:
# - Level 2: API Key authentication (X-Agent-API-Key header)
# - Level 3: JWT Token authentication (Authorization: Bearer header)

import requests
import urllib3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Suppress SSL warnings for self-signed certificates in development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FormPagesAPIClient:
    """
    API client for Form Pages Locator feature.
    Replaces direct server method calls with HTTP API calls.
    """
    
    def __init__(
        self, 
        api_url: str, 
        agent_token: str,
        company_id: int,
        product_id: int,
        project_id: int,
        network_id: int,
        crawl_session_id: int,
        user_id: int = 0,
        ssl_verify: bool = False,
        api_key: str = "",
        jwt_token: str = ""
    ):
        """
        Initialize API client.
        
        Args:
            api_url: Base URL of API server (e.g., https://localhost)
            agent_token: Agent authentication token (legacy)
            company_id: Company ID
            product_id: Product ID
            project_id: Project ID
            network_id: Network ID
            crawl_session_id: Current crawl session ID
            user_id: User ID for API usage tracking
            ssl_verify: Whether to verify SSL certificates (False for self-signed)
            api_key: Level 2 - API key for authentication
            jwt_token: Level 3 - JWT token for session authentication
        """
        self.api_url = api_url.rstrip('/')
        self.agent_token = agent_token
        self.company_id = company_id
        self.product_id = product_id
        self.project_id = project_id
        self.network_id = network_id
        self.crawl_session_id = crawl_session_id
        self.user_id = user_id
        self.ssl_verify = ssl_verify
        self.api_key = api_key
        self.jwt_token = jwt_token
        
        # Track created form names (to avoid duplicates)
        self.created_form_names: List[str] = []
        
        # Track new form pages count
        self.new_form_pages_count = 0
        self.max_form_pages: Optional[int] = None
        
        # UI verification flag
        self.ui_verification = True
        
        # Store parent fields for current form
        self.current_form_parent_fields: List[Dict] = []
    
    def _headers(self) -> Dict[str, str]:
        """Get request headers with API key and JWT token"""
        self._ensure_valid_jwt()
        headers = {
            "Content-Type": "application/json"
        }
        
        # Level 2: API Key (permanent identity)
        if self.api_key:
            headers["X-Agent-API-Key"] = self.api_key
        
        # Level 3: JWT Token (short-lived session)
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        elif self.agent_token:
            # Fallback to legacy token if no JWT
            headers["Authorization"] = f"Bearer {self.agent_token}"
        
        return headers
    
    def update_jwt_token(self, jwt_token: str):
        """Update the JWT token (called when token is refreshed)"""
        self.jwt_token = jwt_token

    def _ensure_valid_jwt(self):
        """Refresh JWT if expired or about to expire (5 min buffer)."""
        if not self.jwt_token or not self.api_key:
            return

        if not hasattr(self, '_jwt_expires_at') or not self._jwt_expires_at:
            # First call - assume token valid, set expiry 25 min from now
            self._jwt_expires_at = datetime.utcnow() + timedelta(minutes=25)
            return

        # Refresh 5 minutes before expiry
        if datetime.utcnow() >= self._jwt_expires_at - timedelta(minutes=5):
            try:
                url = f"{self.api_url}/api/agent/refresh-token"
                headers = {"X-Agent-API-Key": self.api_key}
                response = requests.post(url, headers=headers, timeout=30, verify=self.ssl_verify)
                if response.status_code == 200:
                    result = response.json()
                    self.jwt_token = result['jwt']
                    expires_in = result.get('expires_in', 1800)
                    self._jwt_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    print(f"[APIClient] ✅ JWT refreshed (expires in {expires_in}s)")
                else:
                    print(f"[APIClient] ❌ JWT refresh failed: HTTP {response.status_code}")
            except Exception as e:
                print(f"[APIClient] ❌ JWT refresh error: {e}")

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to API"""
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.post(url, json=data, headers=self._headers(), timeout=120, verify=self.ssl_verify)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] ❌ POST {endpoint} failed: {e}")
            return {"error": str(e)}
    
    def _put(self, endpoint: str, data: Dict) -> Dict:
        """Make PUT request to API"""
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.put(url, json=data, headers=self._headers(), timeout=30, verify=self.ssl_verify)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] ❌ PUT {endpoint} failed: {e}")
            return {"error": str(e)}
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to API"""
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.get(url, params=params, headers=self._headers(), timeout=30, verify=self.ssl_verify)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] ❌ GET {endpoint} failed: {e}")
            return {"error": str(e)}
    
    # ========== CRAWL SESSION ==========
    
    def update_crawl_session(
        self,
        status: Optional[str] = None,
        pages_crawled: Optional[int] = None,
        forms_found: Optional[int] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """Update crawl session status"""
        data = {}
        if status:
            data["status"] = status
        if pages_crawled is not None:
            data["pages_crawled"] = pages_crawled
        if forms_found is not None:
            data["forms_found"] = forms_found
        if error_message:
            data["error_message"] = error_message
        if error_code:
            data["error_code"] = error_code
        
        self._put(f"/api/form-pages/sessions/{self.crawl_session_id}", data)
    
    # ========== AI OPERATIONS ==========

    def generate_login_steps(
            self,
            page_html: str,
            screenshot_base64: str,
            username: str,
            password: str,
            login_url: str = ""
    ) -> List[Dict[str, Any]]:
        """Generate login automation steps using AI"""
        print("[APIClient] 🔑 Requesting login steps from server...")
        
        result = self._post("/api/form-pages/ai/login-steps", {
            "page_html": page_html,
            "screenshot_base64": screenshot_base64,
            "username": username,
            "password": password,
            "login_url": login_url,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        steps = result.get("steps", [])
        print(f"[APIClient] 🔑 Received {len(steps)} login steps")
        return steps
    
    def generate_logout_steps(
        self,
        page_html: str,
        screenshot_base64: str
    ) -> List[Dict[str, Any]]:
        """Generate logout automation steps using AI"""
        print("[APIClient] 🚪 Requesting logout steps from server...")
        
        result = self._post("/api/form-pages/ai/logout-steps", {
            "page_html": page_html,
            "screenshot_base64": screenshot_base64,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        steps = result.get("steps", [])
        print(f"[APIClient] 🚪 Received {len(steps)} logout steps")
        return steps
    
    def extract_form_name(
        self,
        context_data: Dict[str, Any],
        page_html: str = "",
        screenshot_base64: str = None
    ) -> str:
        """Extract semantic form name using AI"""
        print("[APIClient] AI: Extracting form name...")
        
        result = self._post("/api/form-pages/ai/form-name", {
            "url": context_data.get("url", ""),
            "url_path": context_data.get("url_path", ""),
            "button_clicked": context_data.get("button_clicked", ""),
            "page_title": context_data.get("page_title", ""),
            "headers": context_data.get("headers", []),
            "form_labels": context_data.get("form_labels", []),
            "existing_names": self.created_form_names,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        form_name = result.get("form_name", "unknown_form")
        print(f"[APIClient] AI: ✅ Form name: '{form_name}'")
        
        # Also extract parent reference fields
        print("[APIClient] AI: Extracting parent reference fields...")
        self.current_form_parent_fields = self.extract_parent_reference_fields(
            form_name, page_html, screenshot_base64
        )
        print(f"[APIClient] AI: ✅ Found {len(self.current_form_parent_fields)} parent fields")
        
        return form_name
    
    def extract_parent_reference_fields(
        self,
        form_name: str,
        page_html: str,
        screenshot_base64: str = None
    ) -> List[Dict[str, Any]]:
        """Extract parent reference fields using AI"""
        result = self._post("/api/form-pages/ai/parent-fields", {
            "form_name": form_name,
            "page_html": page_html,
            "screenshot_base64": screenshot_base64,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        return result.get("fields", [])
    
    def verify_ui_defects(self, form_name: str, screenshot_base64: str) -> str:
        """Check for UI defects using AI Vision"""
        if not self.ui_verification or not screenshot_base64:
            return ""
        
        print(f"[APIClient] AI: Checking UI for defects...")
        
        result = self._post("/api/form-pages/ai/ui-defects", {
            "form_name": form_name,
            "screenshot_base64": screenshot_base64,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        defects = result.get("defects", "")
        if defects:
            print(f"[APIClient] ⚠️ UI Defects detected: {defects}")
        else:
            print(f"[APIClient] ✅ No UI defects detected")
        
        return defects
    
    def is_submission_button(self, button_text: str, screenshot_base64: str = None) -> bool:
        """Determine if button is a form submission button"""
        result = self._post("/api/form-pages/ai/is-submission-button", {
            "button_text": button_text,
            "screenshot_base64": screenshot_base64,
            "network_id": self.network_id,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        
        return result.get("is_submission", False)
    
    def get_navigation_clickables(self, screenshot_base64: str) -> List[str]:
        """Ask AI to identify navigation clickables from screenshot"""
        result = self._post("/api/form-pages/ai/navigation-clickables", {
            "screenshot_base64": screenshot_base64,
            "company_id": self.company_id,
            "product_id": self.product_id,
            "user_id": self.user_id,
            "crawl_session_id": self.crawl_session_id
        })
        return result.get("clickables", [])
    
    # ========== FORM ROUTE OPERATIONS ==========
    
    def check_form_exists(self, project_name: str, form_url: str) -> bool:
        """Check if form with this URL already exists"""
        result = self._get("/api/form-pages/routes", {
            "network_id": self.network_id
        })
        
        if "error" in result:
            return False
        
        # Normalize URL for comparison
        url_base = form_url.split('#')[0].split('?')[0]
        
        for route in result:
            existing_url = route.get("url", "")
            existing_url_base = existing_url.split('#')[0].split('?')[0]
            if url_base == existing_url_base:
                print(f"[APIClient] ⭐ Form URL already exists: {url_base}")
                return True
        
        return False
    
    def create_form_folder(
        self,
        project_name: str,
        form: Dict[str, Any],
        username: str = None,
        login_url: str = None
    ) -> bool:
        """Save discovered form route to database."""
        # Check limit
        if self.max_form_pages is not None and self.new_form_pages_count >= self.max_form_pages:
            print(f"[APIClient] ⛔ Limit reached: {self.new_form_pages_count}/{self.max_form_pages}")
            return False
        
        form_name = form.get("form_name")
        
        # Extract parent field names
        id_fields = [field.get("field_name") for field in self.current_form_parent_fields]
        
        # Save to database via API
        result = self._post("/api/form-pages/routes", {
            "company_id": self.company_id,
            "product_id": self.product_id,
            "project_id": self.project_id,
            "network_id": self.network_id,
            "crawl_session_id": self.crawl_session_id,
            "form_name": form_name,
            "url": form.get("form_url"),
            "login_url": login_url or "",
            "username": username or "unknown",
            "navigation_steps": form.get("navigation_steps", []),
            "id_fields": id_fields,
            "parent_fields": self.current_form_parent_fields,
            "is_root": True,
            "verification_attempts": 1
        })
        
        if "error" not in result:
            self.new_form_pages_count += 1
            
            # Track form name
            if form_name not in self.created_form_names:
                self.created_form_names.append(form_name)
            
            print(f"[APIClient] ✅ Saved form route: {form_name} ({self.new_form_pages_count}/{self.max_form_pages or '∞'})")
            return True
        else:
            print(f"[APIClient] ❌ Failed to save form route: {result.get('error')}")
            return False
    
    def update_form_verification(
        self,
        project_name: str,
        form_name: str,
        navigation_steps: List[Dict[str, Any]],
        verification_attempts: int = 1
    ):
        """Update form route with verified navigation steps"""
        print(f"[APIClient] ✅ Form '{form_name}' verified (attempts: {verification_attempts})")
    
    def build_hierarchy(self, project_name: str = None) -> Dict[str, Any]:
        """Build parent-child relationships for all routes"""
        print("[APIClient] 🔗 Building hierarchy...")
        
        result = self._post("/api/form-pages/routes/build-hierarchy", {
            "network_id": self.network_id
        })
        
        if "error" not in result:
            print("[APIClient] ✅ Hierarchy built")
        else:
            print(f"[APIClient] ⚠️ Hierarchy build failed: {result.get('error')}")
        
        return {"ordered_forms": self.created_form_names}
    
    # ========== UTILITY ==========
    
    def health_check(self) -> Dict[str, Any]:
        """Check API server health"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5, verify=self.ssl_verify)
            return {"status": "ok", "server_reachable": response.status_code == 200}
        except:
            return {"status": "error", "server_reachable": False}
    
    def get_ai_cost_summary(self) -> Dict[str, Any]:
        """Placeholder - cost tracking is done server-side"""
        return {
            "api_calls": 0,
            "total_cost": 0.0,
            "note": "Cost tracking is done server-side"
        }
    
    def print_ai_cost_summary(self):
        """Placeholder - cost tracking is done server-side"""
        print("\n[APIClient] 💰 AI costs tracked server-side\n")
