#!/usr/bin/env python3
"""
Form Discoverer Agent - Main Entry Point (WEB UI VERSION)
Location: web_services_product/agent/main.py

Runs on customer's network, connects to api-server, executes Selenium automation
Now with web-based UI and system tray icon!

Security Levels:
- Level 1: HTTPS/SSL (encrypted communication)
- Level 2: API Key (permanent agent identity)
- Level 3: JWT Token (short-lived access, auto-refresh)

UPDATED: Added JWT token handling with auto-refresh before expiry
UPDATED: Added Form Mapper task handling
"""

import os
import sys
import time
import logging
import requests
import urllib3
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from agent_config import AgentConfig
from agent_selenium import AgentSelenium
from tray_icon import AgentTrayIcon
from traffic_capture import TrafficCapture
from web_ui.server import start_server
from crawler import FormPagesCrawler, FormPagesAPIClient
from crawler.form_pages_utils import detect_page_error, PageErrorCode, get_error_message
from form_mapper_handler import FormMapperTaskHandler
from activity_logger import init_activity_logger, get_activity_logger

# Suppress SSL warnings for self-signed certificates in development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_first_run():
    """Check if this is first run (no .env file)"""
    env_file = Path('.env')
    return not env_file.exists()


class FormDiscovererAgent:
    """Main agent that connects to the server and coordinates operations"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = AgentConfig(config_file)
        self.activity_logger = init_activity_logger(self.config)
        self._setup_logging()
        self.selenium_agent = AgentSelenium()  # Uses default Desktop path
        self.is_running = False
        self.current_task_id = None
        self.current_crawl_session_id = None  # Track current crawl session for cancel
        self.heartbeat_thread = None
        self.tray_icon = None
        self.cancel_requested = False  # Set by heartbeat when server requests cancellation
        
        # Initialize Form Mapper handler
        self.form_mapper_handler = FormMapperTaskHandler(self.selenium_agent)
        self.logger.info("✓ Form Mapper handler initialized")
        
        # SSL verification setting (False for self-signed certs)
        self.ssl_verify = getattr(self.config, 'ssl_verify', False)
        
        # Level 2: API Key for authentication (permanent)
        self.api_key = getattr(self.config, 'api_key', '')
        
        # Level 3: JWT Token for session access (short-lived)
        self.jwt_token = None
        self.jwt_expires_at = None
        
        # Initialize traffic capture if enabled
        if getattr(self.config, 'capture_traffic', False):
            traffic_storage = Path(self.config.log_folder) / 'traffic' if self.config.log_folder else None
            self.traffic = TrafficCapture(enabled=True, storage_path=traffic_storage)
            self.logger.info("✓ Browser traffic capture enabled")
        else:
            self.traffic = None
            self.logger.info("✓ Browser traffic capture disabled")
        
        # Log header to console AND to selenium_agent's results_logger (customer-facing)
        header_lines = [
            "="*70,
            "Form Discoverer Agent Initialized",
            "="*70
        ]
        for line in header_lines:
            self.logger.info(line)
            self.activity_logger.info(line)
    
    def _setup_logging(self):
        # Console-only logger for system messages (not written to file)
        self.logger = logging.getLogger('FormDiscovererAgent')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False
        
        # Console handler only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)
    
    def _ensure_valid_jwt(self):
        """
        Ensure we have a valid JWT token. Refresh if expired or about to expire.
        Called before any protected API request.
        """
        if not self.jwt_token or not self.jwt_expires_at:
            # No JWT yet - need to register first
            return
        
        # Refresh 5 minutes before expiry to avoid race conditions
        refresh_threshold = self.jwt_expires_at - timedelta(minutes=5)
        
        if datetime.utcnow() >= refresh_threshold:
            self.logger.info("🔄 JWT token expiring soon, refreshing...")
            self._refresh_jwt()
    
    def _refresh_jwt(self):
        """
        Get a new JWT token using our API key.
        Called when JWT expires or is about to expire.
        """
        if not self.api_key:
            self.logger.error("❌ Cannot refresh JWT: No API key")
            return False
        
        try:
            url = f"{self.config.api_url}/api/agent/refresh-token"
            headers = {
                "X-Agent-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, timeout=30, verify=self.ssl_verify)
            
            if response.status_code == 200:
                result = response.json()
                self.jwt_token = result['jwt']
                expires_in = result.get('expires_in', 1800)  # Default 30 min
                self.jwt_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                self.logger.info(f"✅ JWT token refreshed (expires in {expires_in}s)")
                self.activity_logger.update_auth(api_key=self.api_key, jwt_token=self.jwt_token)
                return True
            elif response.status_code == 401:
                # API key invalidated - another agent took over
                self.logger.error("❌ Session invalidated - another agent connected for this user")
                self.logger.error("   This agent is now disabled. Please re-register.")
                self._handle_session_invalidated()
                return False
            else:
                self.logger.error(f"❌ JWT refresh failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ JWT refresh error: {str(e)}")
            return False
    
    def _handle_session_invalidated(self):
        """Handle case where another agent has taken over this user's session."""
        self.logger.error("="*70)
        self.logger.error("SESSION INVALIDATED")
        self.logger.error("Another agent has registered for this user.")
        self.logger.error("This agent is now permanently disabled.")
        self.logger.error("To use this machine, re-run the agent to re-register.")
        self.logger.error("="*70)
        
        # Update tray icon to show error
        if self.tray_icon:
            self.tray_icon.update_status(False)
        
        # Stop the agent
        self.is_running = False
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with API key AND JWT token.
        Automatically refreshes JWT if needed.
        """
        # Ensure JWT is valid before making request
        self._ensure_valid_jwt()
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Level 2: API Key (always include if we have it)
        if self.api_key:
            headers["X-Agent-API-Key"] = self.api_key
        
        # Level 3: JWT Token (always include if we have it)
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        return headers
    
    def connect_to_server(self) -> bool:
        """
        Register with server and receive API key + JWT token.
        If we already have an API key, this will generate a NEW one
        (invalidating any other agent for this user).
        """
        try:
            self.logger.info("Connecting to server...")
            url = f"{self.config.api_url}/api/agent/register"
            
            # Registration doesn't require auth headers
            headers = {
                "Authorization": f"Bearer {self.config.agent_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "agent_id": self.config.agent_id,
                "company_id": self.config.company_id,
                "user_id": self.config.user_id,
                "hostname": os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'unknown')),
                "platform": sys.platform,
                "version": "2.0.0"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30, verify=self.ssl_verify)
            
            if response.status_code == 200:
                result = response.json()
                
                # Save API key (Level 2)
                if result.get('api_key'):
                    self.api_key = result['api_key']
                    self.config.save_api_key(self.api_key)
                    self.logger.info("✅ API key received and saved")
                
                # Save JWT token (Level 3)
                if result.get('jwt'):
                    self.jwt_token = result['jwt']
                    expires_in = result.get('expires_in', 1800)
                    self.jwt_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    self.logger.info(f"✅ JWT token received (expires in {expires_in}s)")
                    self.activity_logger.update_auth(api_key=self.api_key, jwt_token=self.jwt_token)
                
                self.logger.info(f"✅ Connected successfully")
                
                # Update tray icon status
                if self.tray_icon:
                    self.tray_icon.update_status(True)
                return True
            else:
                self.logger.error(f"❌ Failed: HTTP {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                    self.logger.error(f"   Detail: {error_detail}")
                except:
                    pass
                if self.tray_icon:
                    self.tray_icon.update_status(False)
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Connection error: {str(e)}")
            if self.tray_icon:
                self.tray_icon.update_status(False)
            return False
    
    def send_heartbeat(self):
        """Send periodic heartbeats to server."""
        while self.is_running:
            try:
                url = f"{self.config.api_url}/api/agent/heartbeat"
                payload = {
                    "agent_id": self.config.agent_id,
                    "status": "idle" if not self.current_task_id else "busy",
                    "current_task_id": self.current_task_id,
                    "current_crawl_session_id": self.current_crawl_session_id
                }
                
                response = requests.post(url, json=payload, headers=self._get_headers(), timeout=10, verify=self.ssl_verify)
                
                # Update tray icon based on connection
                if self.tray_icon:
                    self.tray_icon.update_status(response.status_code == 200)
                
                # Check for cancel request from server
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('cancel_requested'):
                            self.logger.info("⏹ Cancel requested by server")
                            self.cancel_requested = True
                    except:
                        pass
                
                # Check for authentication errors
                if response.status_code == 401:
                    error_detail = ""
                    try:
                        error_detail = response.json().get('detail', '')
                    except:
                        pass
                    
                    if "Session invalidated" in error_detail or "another agent" in error_detail.lower():
                        # Another agent took over - we're done
                        self._handle_session_invalidated()
                        return
                    elif "Token expired" in error_detail:
                        # JWT expired - try to refresh
                        self.logger.warning("⚠️ JWT expired during heartbeat, refreshing...")
                        if not self._refresh_jwt():
                            self._handle_session_invalidated()
                            return
                    else:
                        # Unknown auth error - try to re-register
                        self.logger.error(f"❌ Heartbeat auth error: {error_detail}")
                        self.connect_to_server()
                    
            except Exception as e:
                self.logger.warning(f"Heartbeat error: {str(e)}")
                if self.tray_icon:
                    self.tray_icon.update_status(False)
            
            time.sleep(30)
    
    def poll_for_tasks(self):
        """Poll server for tasks to execute."""
        self.logger.info("📡 Polling for tasks...")
        consecutive_errors = 0
        
        while self.is_running:
            try:
                url = f"{self.config.api_url}/api/agent/poll-task?agent_id={self.config.agent_id}&company_id={self.config.company_id}"
                response = requests.get(url, headers=self._get_headers(), timeout=35, verify=self.ssl_verify)
                
                if response.status_code == 200:
                    task = response.json()
                    consecutive_errors = 0
                    if task and task.get('task_id'):
                        self.logger.info(f"📥 Received task: {task.get('task_id')}")
                        self.execute_task(task)
                elif response.status_code == 204:
                    consecutive_errors = 0
                    # Check if cancel was requested while idle
                    if self.cancel_requested:
                        self.logger.info("⏹ Cancel requested - closing browser")
                        self.cancel_requested = False
                        # Mark all active sessions as closed
                        if hasattr(self, 'form_mapper_handler') and self.form_mapper_handler:
                            self.form_mapper_handler.closed_sessions.update(
                                self.form_mapper_handler.active_sessions.keys())

                        if self.selenium_agent.driver:
                            self.selenium_agent.close_browser()
                    time.sleep(1)
                elif response.status_code == 401:
                    error_detail = ""
                    try:
                        error_detail = response.json().get('detail', '')
                    except:
                        pass
                    
                    if "Session invalidated" in error_detail or "another agent" in error_detail.lower():
                        self._handle_session_invalidated()
                        return
                    elif "Token expired" in error_detail:
                        self.logger.warning("⚠️ JWT expired during poll, refreshing...")
                        if not self._refresh_jwt():
                            self._handle_session_invalidated()
                            return
                    else:
                        self.logger.error(f"❌ Poll auth error: {error_detail}")
                        consecutive_errors += 1
                        time.sleep(5)
                else:
                    consecutive_errors += 1
                    self.logger.error(f"Poll returned status code: {response.status_code}")
                    time.sleep(5)
                    
            except requests.exceptions.Timeout:
                consecutive_errors = 0
                pass
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Poll error: {str(e)}")
                time.sleep(5)
            
            # Exponential backoff on repeated errors
            if consecutive_errors > 5:
                wait_time = min(60, 5 * consecutive_errors)
                self.logger.warning(f"Multiple errors, waiting {wait_time}s...")
                time.sleep(wait_time)
    
    def execute_task(self, task: dict):
        """Execute a received task."""
        task_id = task.get('task_id')
        task_type = task.get('task_type')
        parameters = task.get('parameters', {})
        
        self.current_task_id = task_id
        self.logger.info(f"▶️ Executing: {task_type}")
        
        try:
            # Update status to running
            # Update status to running
            self._update_task_status(task_id, 'running')


            # ===== FORM MAPPER TASKS =====
            if task_type.startswith('form_mapper_'):
                self.cancel_requested = False  # Reset cancel flag for new task
                self.logger.info(f"🗺️ Form Mapper task: {task_type}")
                result = self.form_mapper_handler.handle_task(task)

                # Report result back to Form Mapper endpoint
                self._report_form_mapper_result(result)

                # Check if cancel was requested during execution
                if self.cancel_requested:
                    self.logger.info("⏹ Cancel requested - closing browser")
                    self.cancel_requested = False
                    session_id = task.get("session_id")
                    if session_id:
                        try:
                            self.form_mapper_handler.closed_sessions.add(int(session_id))
                        except (ValueError, TypeError):
                            pass

                    if self.selenium_agent.driver:
                        self.selenium_agent.close_browser()
                    return

                if result.get('success'):
                    self._update_task_status(task_id, 'completed', result=result)
                    self.logger.info(f"✅ Form Mapper task completed: {task_type}")
                else:
                    self._update_task_status(task_id, 'failed', error=result.get('error'))
                    self.logger.error(f"❌ Form Mapper task failed: {result.get('error')}")
                return
            # ===== END FORM MAPPER TASKS =====

            # ===== FORMS RUNNER TASKS =====
            if task_type.startswith('forms_runner_'):
                self.cancel_requested = False  # Reset cancel flag for new task
                self.logger.info(f"🏃 Forms Runner task: {task_type}")
                result = self.form_mapper_handler.handle_task(task)
                self._report_form_mapper_result(result)

                # Check if cancel was requested during execution
                if self.cancel_requested:
                    self.logger.info("⏹ Cancel requested - closing browser")
                    self.cancel_requested = False
                    session_id = task.get("session_id")
                    if session_id:
                        try:
                            self.form_mapper_handler.closed_sessions.add(int(session_id))
                        except (ValueError, TypeError):
                            pass
                    if self.selenium_agent.driver:
                        self.selenium_agent.close_browser()
                    return

                if result.get('success'):
                    self._update_task_status(task_id, 'completed', result=result)
                    self.logger.info(f"✅ Forms Runner task completed: {task_type}")
                else:
                    self._update_task_status(task_id, 'failed', error=result.get('error'))
                    self.logger.error(f"❌ Forms Runner task failed: {result.get('error')}")
                return
            # ===== END FORMS RUNNER TASKS =====

            # Execute based on type
            if task_type == 'discover_form_pages':
                result = self._handle_discover_form_pages(parameters)
            elif task_type == 'execute_test':
                result = self._handle_execute_test(parameters)
            elif task_type == 'execute_steps':
                result = self._handle_execute_steps(parameters)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            # Report result
            if result.get('success'):
                self._update_task_status(task_id, 'completed', result=result)
                self.logger.info(f"✅ Task completed: {task_id}")
            else:
                self._update_task_status(task_id, 'failed', error=result.get('error'))
                self.logger.error(f"❌ Task failed: {result.get('error')}")
                # Log to results_logger so it shows in web UI logs
                self.activity_logger.error(f"❌ TASK FAILED: {result.get('error')}")
                
        except Exception as e:
            self.logger.exception(f"Task error: {str(e)}")
            self._update_task_status(task_id, 'failed', error=str(e))
            # Log to results_logger so it shows in web UI logs
            self.activity_logger.error(f"❌ TASK ERROR: {str(e)}")
        finally:
            self.current_task_id = None
    
    def _update_task_status(self, task_id: str, status: str, result: dict = None, error: str = None):
        """Send task status update to server."""
        try:
            url = f"{self.config.api_url}/api/agent/task-status"
            payload = {
                "task_id": task_id,
                "status": status,
                "message": error,
                "result": result
            }
            requests.post(url, json=payload, headers=self._get_headers(), timeout=30, verify=self.ssl_verify)
        except Exception as e:
            self.logger.warning(f"Failed to update task status: {e}")
    
    def _report_form_mapper_result(self, result: Dict):
        """Report Form Mapper task result back to server."""
        try:
            url = f"{self.config.api_url}/api/form-mapper/agent/task-result"
            
            payload = {
                "session_id": result.get("session_id"),
                "task_type": result.get("task_type"),
                "success": result.get("success", False),
                "payload": result,
                "error": result.get("error")
            }
            
            # Use API key header for agent endpoint
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=30, 
                verify=self.ssl_verify
            )
            
            if response.status_code == 200:
                resp_data = response.json()
                self.logger.info(f"📤 Form Mapper result reported: {resp_data.get('next_action', 'ok')}")
            else:
                self.logger.warning(f"⚠️ Form Mapper result report failed: HTTP {response.status_code}")
                self.logger.warning(
                    f"⚠️ Form Mapper result report failed: HTTP {response.status_code} - {response.text}")
                
        except Exception as e:
            self.logger.error(f"❌ Error reporting Form Mapper result: {e}")
    
    def _handle_execute_steps(self, params: Dict) -> Dict:
        """Execute Selenium steps."""
        steps = params.get('steps', [])
        
        for i, step in enumerate(steps):
            result = self.selenium_agent.execute_step(step)
            if not result.get('success'):
                return {"success": False, "error": f"Step {i} failed: {result.get('message')}"}
        
        return {"success": True, "message": f"Executed {len(steps)} steps"}
    
    def _handle_execute_test(self, params: Dict) -> Dict:
        """Execute a test with navigation and test steps."""
        nav_steps = params.get('navigation_steps', [])
        test_steps = params.get('test_steps', [])
        
        nav_result = self._handle_execute_steps({'steps': nav_steps})
        if not nav_result.get('success'):
            return nav_result
        
        return self._handle_execute_steps({'steps': test_steps})

    def _handle_discover_form_pages(self, params: Dict) -> Dict:
        """Handle form page discovery task."""
        self.logger.info("🔍 Starting form page discovery...")

        crawl_session_id = params.get('crawl_session_id')
        self.current_crawl_session_id = crawl_session_id  # Track for cancel detection
        # Start activity logging session
        self.activity_logger.start_session(
            activity_type='discovery',
            session_id=crawl_session_id,
            project_id=params.get('project_id'),
            company_id=params.get('company_id'),
            user_id=params.get('user_id', 0),
            network_id=params.get('network_id')
        )
        self.activity_logger.info("🔍 Discovery started")
        network_url = params.get('network_url')
        login_url = params.get('login_url', network_url)
        login_username = params.get('login_username')
        login_password = params.get('login_password')
        project_name = params.get('project_name', 'default')
        max_depth = params.get('max_depth', 20)
        max_form_pages = params.get('max_form_pages')
        slow_mode = params.get('slow_mode', True)
        
        # Re-read browser settings from .env file (allows changes without restart)
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Reload .env to pick up changes
        headless = os.getenv('DEFAULT_HEADLESS', 'false').lower() == 'true'
        browser = os.getenv('BROWSER', 'chrome')
        self.logger.info(f"[Browser Config] browser={browser}, headless={headless} (fresh from .env)")

        api_client = FormPagesAPIClient(
            api_url=self.config.api_url,
            agent_token=self.config.agent_token,
            company_id=params.get('company_id'),
            product_id=params.get('product_id'),
            project_id=params.get('project_id'),
            network_id=params.get('network_id'),
            crawl_session_id=crawl_session_id,
            user_id=params.get('user_id', 0),
            ssl_verify=self.ssl_verify,
            api_key=self.api_key,
            jwt_token=self.jwt_token  # Pass JWT to client
        )
        api_client.max_form_pages = max_form_pages

        api_client.update_crawl_session(status='running')

        try:
            # Always close existing browser and create fresh session
            if self.selenium_agent.driver:
                self.logger.info("Closing existing browser session...")
                try:
                    self.selenium_agent.close_browser()
                except Exception as e:
                    self.logger.warning(f"Error closing old browser: {e}")
            
            # Create fresh browser
            self.selenium_agent.initialize_browser(
                browser_type=browser,
                headless=headless
            )

            driver = self.selenium_agent.driver
            driver.get(login_url)
            time.sleep(2)
            
            # Check for page error after initial load
            page_error = detect_page_error(driver)
            if page_error:
                error_msg = get_error_message(page_error)
                self.logger.error(f"Initial page error: {error_msg}")
                self.activity_logger.error(f"❌ PAGE ERROR: {error_msg}")
                api_client.update_crawl_session(
                    status='failed',
                    error_code=page_error,
                    error_message=f"Cannot access site: {error_msg}"
                )
                return {"success": False, "error": error_msg, "error_code": page_error}

            # Login with retry logic
            login_successful = False
            if login_username and login_password:
                self.logger.info(f"Logging in as: {login_username}")
                
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                max_login_attempts = 3
                for attempt in range(1, max_login_attempts + 1):
                    self.logger.info(f"Login attempt {attempt}/{max_login_attempts}")
                    
                    try:
                        # Get fresh page state for each attempt
                        page_html = driver.execute_script("return document.documentElement.outerHTML")
                        screenshot_b64 = driver.get_screenshot_as_base64()

                        login_steps = api_client.generate_login_steps(
                            page_html=page_html,
                            screenshot_base64=screenshot_b64,
                            username=login_username,
                            password=login_password,
                            login_url = login_url
                        )
                        
                        if not login_steps:
                            # AI returned no steps - not a login page (or already logged in)
                            # Assume we're on the dashboard and continue to crawl
                            self.logger.info("No login steps returned - assuming already on dashboard, continuing...")
                            login_successful = True
                            break

                        # Execute login steps with error handling per step
                        step_failed = False
                        for step in login_steps:
                            action = step.get('action')
                            selector = step.get('selector')
                            value = step.get('value', '')

                            try:
                                if action == 'fill':
                                    # Wait for element to be present
                                    element = WebDriverWait(driver, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                    )
                                    element.clear()
                                    element.send_keys(value)
                                    time.sleep(0.3)
                                elif action == 'click':
                                    # Wait for element to be clickable
                                    element = WebDriverWait(driver, 10).until(
                                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                    )
                                    element.click()
                                    time.sleep(0.5)
                                elif action in ('wait_dom_ready', 'verify_clickables'):
                                    time.sleep(1)
                            except Exception as step_error:
                                self.logger.warning(f"Login step failed: {action} on '{selector}': {step_error}")
                                step_failed = True
                                break
                        
                        if step_failed:
                            if attempt < max_login_attempts:
                                self.logger.info(f"Retrying login...")
                                driver.get(login_url)
                                time.sleep(2)
                                continue
                            break

                        # Wait for page to load after login
                        time.sleep(2)
                        
                        # Check if login succeeded (not on login page anymore, no error)
                        page_error = detect_page_error(driver)
                        if page_error:
                            self.logger.warning(f"Page error after login attempt: {page_error}")
                            if attempt < max_login_attempts:
                                driver.get(login_url)
                                time.sleep(2)
                                continue
                            break
                        
                        # Login succeeded
                        login_successful = True
                        self.logger.info(f"✅ Login successful on attempt {attempt}")
                        self.activity_logger.info("✅ Login successful")
                        break
                        
                    except Exception as login_error:
                        self.logger.error(f"Login attempt {attempt} failed: {login_error}")
                        if attempt < max_login_attempts:
                            driver.get(login_url)
                            time.sleep(2)
                            continue
                        break
                
                # Check if all login attempts failed
                if not login_successful:
                    error_msg = f"Login failed after {max_login_attempts} attempts"
                    self.logger.error(error_msg)
                    self.activity_logger.error(f"❌ {error_msg}")
                    api_client.update_crawl_session(
                        status='failed',
                        error_code=PageErrorCode.LOGIN_FAILED,
                        error_message=error_msg
                    )
                    return {"success": False, "error": error_msg, "error_code": PageErrorCode.LOGIN_FAILED}
            else:
                # No login required
                login_successful = True

            base_url = driver.current_url

            # Reset cancel flag before starting crawl
            self.cancel_requested = False

            crawler = FormPagesCrawler(
                driver=driver,
                start_url=base_url,
                base_url=base_url,
                project_name=project_name,
                max_depth=max_depth,
                target_form_pages=[],
                discovery_only=True,
                slow_mode=slow_mode,
                server=api_client,
                username=login_username,
                login_url=login_url,
                agent=self.selenium_agent,  # Pass selenium_agent for log_message support
                form_agent=self  # Pass FormAgent for cancel_requested check
            )

            crawler.crawl()

            # Generate logout steps after discovery completes
            self._generate_logout_steps(driver, api_client)
            
            # Check for page error after crawl completes
            page_error = detect_page_error(driver)
            forms_found = api_client.new_form_pages_count
            
            if forms_found == 0 and page_error:
                # Crawl ended on error page with no forms
                error_msg = get_error_message(page_error)
                self.logger.warning(f"Crawl ended on error page: {error_msg}")
                api_client.update_crawl_session(
                    status='failed',
                    error_code=page_error,
                    error_message=f"Discovery failed: {error_msg}",
                    forms_found=0
                )
                return {"success": False, "error": error_msg, "error_code": page_error}

            api_client.update_crawl_session(
                status='completed',
                forms_found=forms_found
            )

            self.activity_logger.info(f"✅ Discovery complete - {forms_found} forms found")
            self.activity_logger.complete()

            return {
                "success": True,
                "forms_found": forms_found,
                "crawl_session_id": crawl_session_id
            }

        except Exception as e:
            self.logger.error(f"Form discovery failed: {e}")
            # Log to results_logger so it shows in web UI logs
            self.activity_logger.error(f"❌ DISCOVERY FAILED: {e}")
            self.activity_logger.complete()  # Still send logs even on failure
            # Try to detect page error for better error reporting
            error_code = PageErrorCode.UNKNOWN
            try:
                if self.selenium_agent.driver:
                    detected_error = detect_page_error(self.selenium_agent.driver)
                    if detected_error:
                        error_code = detected_error
            except:
                pass
            api_client.update_crawl_session(
                status='failed',
                error_code=error_code,
                error_message=str(e)
            )
            return {"success": False, "error": str(e), "error_code": error_code}
        
        finally:
            self.current_crawl_session_id = None  # Clear session tracking
            if self.selenium_agent.driver:
                self.logger.info("Closing browser after discovery...")
                try:
                    self.selenium_agent.close_browser()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")

    def _generate_logout_steps(self, driver, api_client):
        """Generate and execute logout steps after discovery (same pattern as login)"""
        try:
            self.logger.info("🚪 Generating logout steps...")
            self.activity_logger.info("🚪 Generating logout steps...")

            screenshot_base64 = driver.get_screenshot_as_base64()
            page_html = driver.page_source

            logout_steps = api_client.generate_logout_steps(page_html, screenshot_base64)

            if not logout_steps:
                self.logger.info("⚠️ No logout steps generated")
                return

            self.logger.info(f"✅ Generated {len(logout_steps)} logout steps")

            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            max_logout_attempts = 3
            for attempt in range(1, max_logout_attempts + 1):
                self.logger.info(f"🚪 Logout attempt {attempt}/{max_logout_attempts}")

                try:
                    step_failed = False
                    for step in logout_steps:
                        action = step.get('action')
                        selector = step.get('selector')
                        value = step.get('value', '')

                        try:
                            if action == 'fill':
                                element = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                                )
                                element.clear()
                                element.send_keys(value)
                                time.sleep(0.3)
                            elif action == 'click':
                                element = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                element.click()
                                time.sleep(0.5)
                            elif action in ('wait_dom_ready', 'verify_login_page'):
                                time.sleep(1)
                        except Exception as step_error:
                            self.logger.warning(f"Logout step failed: {action} on '{selector}': {step_error}")
                            step_failed = True
                            break

                    if step_failed:
                        if attempt < max_logout_attempts:
                            self.logger.info("Retrying logout...")
                            time.sleep(2)
                            continue
                        break

                    self.logger.info("✅ Logout completed")
                    self.activity_logger.info("✅ Logout completed")
                    return

                except Exception as logout_error:
                    self.logger.error(f"Logout attempt {attempt} failed: {logout_error}")
                    if attempt < max_logout_attempts:
                        time.sleep(2)
                        continue
                    break

            self.logger.warning("⚠️ Logout failed after all attempts")

        except Exception as e:
            self.logger.warning(f"⚠️ Error during logout: {e}")



    def start(self):
        """Start the agent."""
        try:
            if not self.connect_to_server():
                self.logger.error("Connection failed")
                return False
            
            self.is_running = True
            self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
            self.heartbeat_thread.start()
            self.logger.info("💓 Heartbeat started")
            
            self.poll_for_tasks()
            return True
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the agent."""
        self.logger.info("Stopping...")
        self.is_running = False
        if self.selenium_agent.driver:
            self.selenium_agent.close_browser()
        if self.tray_icon:
            self.tray_icon.stop()
        self.logger.info("Stopped")


def main():
    print("="*70)
    print("Form Discoverer Agent v2.0.0 (Web UI)")
    print("3-Layer Security: HTTPS + API Key + JWT")
    print("="*70)
    print()
    
    # Check if first run (no .env file)
    if check_first_run():
        print("First run detected - starting setup wizard...")
        print("Opening browser for configuration...")
        start_server(port=5555, open_browser=True)
        return
    
    # Create agent
    agent = FormDiscovererAgent()
    
    # Start system tray icon
    try:
        agent.tray_icon = AgentTrayIcon(agent.config)
        agent.tray_icon.start()
        agent.logger.info("✓ System tray icon started")
    except Exception as e:
        agent.logger.error(f"Failed to start system tray: {e}")
    
    # Start web UI server in background
    web_thread = threading.Thread(
        target=start_server,
        args=(5555, False),
        daemon=True
    )
    web_thread.start()
    agent.logger.info("✓ Web UI server started on http://localhost:5555")
    
    # Start main agent
    agent.start()
    
    print("\nShutdown complete")


if __name__ == "__main__":
    main()
