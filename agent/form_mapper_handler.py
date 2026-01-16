# ============================================================================
# Form Mapper - Agent Task Handler
# ============================================================================
# Handles form_mapper_* tasks on the desktop agent.
# Uses existing AgentSelenium for browser operations.
# ============================================================================

import json
import logging
import hashlib
import time
import base64
from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoAlertPresentException, 
    ElementNotInteractableException, StaleElementReferenceException
)

logger = logging.getLogger(__name__)


class FormMapperTaskHandler:
    """
    Handles Form Mapper and Forms Runner tasks on the desktop agent.
    
    Task Types:
    - form_mapper_init: Initialize browser and navigate to form
    - form_mapper_extract_dom: Extract DOM HTML
    - form_mapper_exec_step: Execute a single test step
    - form_mapper_screenshot: Capture screenshot
    - form_mapper_navigate: Navigate to URL
    - form_mapper_close: Close browser
    - forms_runner_exec_step: Execute login/navigation step (with error context)
    - form_mapper_navigate_to_url: Navigate to URL (orchestrator alias)
    - form_mapper_get_screenshot: Get screenshot with base64 encoding
    - form_mapper_extract_dom_for_recovery: Extract DOM + screenshot for step failure recovery
    - form_mapper_extract_dom_for_alert: Extract DOM after alert detected
    - form_mapper_save_screenshot_and_log: Save screenshot to file and log UI issue
    """
    
    def __init__(self, agent_selenium, activity_logger=None, api_client=None):
        """
        Initialize with existing AgentSelenium instance.
        
        Args:
            agent_selenium: AgentSelenium instance (shared with Form Pages Locator)
            activity_logger: ActivityLogger instance for displaying milestones in Web UI
        """
        self.selenium = agent_selenium
        self.activity_logger = activity_logger
        self.api_client = api_client
        self.active_sessions: Dict[int, Dict] = {}  # Track active sessions
        self.closed_sessions: set = set()  # Track closed/cancelled sessions
    
    def handle_task(self, task: Dict) -> Dict:
        """
        Main entry point - route task to appropriate handler.
        
        Args:
            task: Task dict with task_type, session_id, payload
        
        Returns:
            Result dict with success, task_type, and task-specific data
        """
        task_type = task.get("task_type", "")
        session_id = task.get("session_id")
        payload = task.get("payload", {})


        # Start session if context provided and not already started
        session_context = payload.get("session_context")
        print(
            f"[DEBUG] task_type={task_type}, session_context={session_context}, session_active={self.activity_logger.session_active if self.activity_logger else 'no_logger'}")

        if session_context and self.activity_logger and not self.activity_logger.session_active:
            print(f"[DEBUG] Calling start_session for mapping")
            self.activity_logger.start_session(
                activity_type=session_context.get("activity_type", "mapping"),
                session_id=session_context.get("session_id", 0),
                project_id=session_context.get("project_id", 0),
                company_id=session_context.get("company_id", 0),
                user_id=session_context.get("user_id", 0),
                upload_urls=session_context.get("upload_urls", {}),
                screenshots_folder=self.selenium.screenshots_path if self.selenium else None,
                form_files_folder=self.selenium.files_path if self.selenium else None
            )

        # Display log_message if present
        log_message = payload.get("log_message")
        if log_message and self.activity_logger:
            log_level = payload.get("log_level", "info")
            # Handle multiple lines (e.g., "🗺️ Mapping started\n🔐 Login started")
            for line in log_message.strip().split("\n"):
                if line.strip():
                    if log_level == "error":
                        self.activity_logger.error(line.strip())
                    elif log_level == "warning":
                        self.activity_logger.warning(line.strip())
                    else:
                        self.activity_logger.info(line.strip())

        
        logger.info(f"[FormMapper] Handling {task_type} for session {session_id}")
        # Skip tasks for closed sessions (prevents stale task execution)
        if session_id and task_type != "form_mapper_close":
            try:
                if int(session_id) in self.closed_sessions:
                    logger.info(f"[FormMapper] Skipping {task_type} for closed session {session_id}")
                    return {"success": False, "skipped": True, "reason": "session_closed", "task_type": task_type,
                            "session_id": session_id}
            except (ValueError, TypeError):
                pass
        
        handlers = {
            "form_mapper_init": self._handle_init,
            "form_mapper_extract_dom": self._handle_extract_dom,
            "form_mapper_exec_step": self._handle_exec_step,
            "form_mapper_screenshot": self._handle_screenshot,
            "form_mapper_navigate": self._handle_navigate,
            "form_mapper_close": self._handle_close,
            "forms_runner_exec_step": self._handle_runner_exec_step,  # Forms Runner
            # NEW - Required by distributed orchestrator:
            "form_mapper_navigate_to_url": self._handle_navigate,  # Alias
            "form_mapper_get_screenshot": self._handle_get_screenshot,
            "form_mapper_extract_dom_for_recovery": self._handle_extract_dom_for_recovery,
            "form_mapper_extract_dom_for_alert": self._handle_extract_dom_for_alert,
            "form_mapper_log_bug": self._handle_log_bug,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            return {
                "task_type": task_type,
                "session_id": session_id,
                "success": False,
                "error": f"Unknown task type: {task_type}"
            }
        
        try:
            result = handler(session_id, payload)
            result["task_type"] = task_type
            result["session_id"] = session_id
            return result
            
        except Exception as e:
            logger.error(f"[FormMapper] Error handling {task_type}: {e}", exc_info=True)
            return {
                "task_type": task_type,
                "session_id": session_id,
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # Task Handlers
    # ========================================================================
    
    def _handle_init(self, session_id: int, payload: Dict) -> Dict:
        """
        Initialize browser and navigate to form URL.
        
        Payload:
            url: Form page URL
            login_url: Optional login URL
            username: Optional login username
            password: Optional login password
            navigation_steps: Steps to reach the form
            browser: Browser type (chrome, firefox)
            headless: Run headless
        """
        url = payload.get("url")
        login_url = payload.get("login_url")
        username = payload.get("username")
        password = payload.get("password")
        navigation_steps = payload.get("navigation_steps", [])
        browser = payload.get("browser", "chrome")
        headless = payload.get("headless", False)
        
        # Initialize browser if not already done
        if not self.selenium.driver:
            self.selenium.initialize_browser(browser_type=browser, headless=headless)
        
        # Login if needed
        if login_url and username:
            logger.info(f"[FormMapper] Logging in at {login_url}")
            self.selenium.navigate_to_url(login_url)
            
            # Use existing login logic from selenium
            success = self.selenium.login(
                login_url=login_url,
                username=username,
                password=password
            )
            
            if not success:
                return {
                    "success": False,
                    "error": "Login failed"
                }
        
        # Navigate to form URL
        logger.info(f"[FormMapper] Navigating to {url}")
        self.selenium.navigate_to_url(url)
        
        # Execute navigation steps if provided
        if navigation_steps:
            for step in navigation_steps:
                try:
                    self._execute_navigation_step(step)
                except Exception as e:
                    logger.warning(f"[FormMapper] Navigation step failed: {e}")
        
        # Track session
        self.active_sessions[session_id] = {
            "url": url,
            "started_at": time.time()
        }
        
        # Wait for page to stabilize
        time.sleep(1)
        
        return {
            "success": True,
            "current_url": self.selenium.driver.current_url
        }

    def _handle_extract_dom(self, session_id: int, payload: Dict) -> Dict:
        """
        Extract DOM HTML from current page.

        Payload:
            use_full_dom: Extract full page DOM vs form container only
        """
        use_full_dom = payload.get("use_full_dom", True)

        try:
            if use_full_dom:
                result = self.selenium.extract_dom()
            else:
                result = self.selenium.extract_form_container_with_js()

            # Handle Dict result from agent_selenium
            if isinstance(result, dict):
                if not result.get("success"):
                    return {"success": False, "error": result.get("error", "Failed to extract DOM")}
                dom_html = result.get("dom_html", "")
            else:
                dom_html = result

            if not dom_html:
                return {"success": False, "error": "Failed to extract DOM"}

            return {
                "success": True,
                "dom_html": dom_html,
                "dom_length": len(dom_html)
            }

        except Exception as e:
            return {"success": False, "error": f"DOM extraction failed: {e}"}
    
    def _handle_runner_exec_step(self, session_id: int, payload: Dict) -> Dict:
        """
        Execute a Forms Runner step (login/navigation).
        Same as exec_step but captures DOM + screenshot on failure for AI recovery.
        
        Payload:
            step: Step dict with action, selector, value, etc.
        """
        step = payload.get("step", {})
        
        # Auto-initialize browser if not running or session invalid
        try:
            if self.selenium.driver:
                # Test if session is valid
                _ = self.selenium.driver.current_url
        except Exception as e:
            logger.warning(f"[FormMapper] Browser session invalid, reinitializing: {e}")
            self.selenium.driver = None
        
        if not self.selenium.driver:
            print(f"[FormMapper] Auto-initializing browser for runner")
            logger.info(f"[FormMapper] Auto-initializing browser for runner")
            self.selenium.initialize_browser(browser_type="chrome", headless=False)
            self.active_sessions[session_id] = {"initialized_at": time.time()}



            # Navigate to base URL if provided
            base_url = payload.get("base_url")
            if base_url:
                self.selenium.driver.get(base_url)

        if not step:
            return {"success": False, "error": "No step provided"}
        
        # Execute the step using existing logic
        result = self._handle_exec_step(session_id, {"step": step})
        
        # On failure, capture context for AI recovery
        if not result.get("success"):
            try:
                # Capture DOM
                dom_html = self.selenium.extract_dom() or ""
                #dom_result = self.selenium.extract_dom()
                #print(f"[DEBUG] extract_dom returned type: {type(dom_result)}")
                #print(f"[DEBUG] extract_dom returned: {str(dom_result)[:200]}")
                #dom_html = dom_result or ""
                #print(f"[DEBUG] dom_html type: {type(dom_html)}")

                # Capture full page screenshot
                screenshot_b64 = ""
                try:
                    screenshot_result = self.selenium.capture_screenshot(scenario_description="error_context",
                                                                         save_to_folder=False)
                    if screenshot_result.get("success"):
                        screenshot_b64 = screenshot_result.get("screenshot", "")
                except:
                    pass
                
                result["dom_html"] = dom_html
                result["screenshot_base64"] = screenshot_b64
                
            except Exception as e:
                logger.warning(f"[FormMapper] Failed to capture error context: {e}")
        
        return result

    def _handle_exec_step(self, session_id: int, payload: Dict) -> Dict:
        """
        Execute a single test step.

        Payload:
            step: Step dict with action, selector, value, etc.
            step_index: Index of step being executed
        """
        step = payload.get("step", {})
        step_index = payload.get("step_index", 0)

        action = step.get("action", "")
        selector = step.get("selector", "")
        wait_seconds = step.get("wait_seconds", 0.5)

        logger.info(f"[FormMapper] Executing step {step_index}: {action} on {selector[:50] if selector else 'N/A'}")

        # Special handling for fill_autocomplete (requires AI field-assist)
        if action == "fill_autocomplete":
            result = self._handle_fill_autocomplete(session_id, step)
        else:
            # Execute the step using agent_selenium (returns full result with fields_changed)
            result = self.selenium.execute_step(step)

        print(f"[DEBUG] execute_step result: {result}")

        # DEBUG: Print step info and full_xpath
        print(f"[Handler] Step result: success={result.get('success')}, action={step.get('action')}")
        print(f"[Handler] Step has full_xpath: {bool(step.get('full_xpath'))}, value: {step.get('full_xpath', 'NONE')[:80] if step.get('full_xpath') else 'NONE'}")

        # If failed and full_xpath exists and it's a locator error - try fallback
        # Don't try fallback for content mismatch (element found but wrong value)
        is_locator_error = result.get("locator_error") or "not found" in result.get("error", "").lower()
        if not result.get("success") and step.get("full_xpath") and is_locator_error:
            original_error = result.get("error", "unknown")
            full_xpath = step.get("full_xpath")
            print(f"[Handler] Primary selector failed, trying full_xpath fallback: {full_xpath}...")

            fallback_step = step.copy()
            fallback_step["selector"] = full_xpath

            if action == "fill_autocomplete":
                fallback_result = self._handle_fill_autocomplete(session_id, fallback_step)
            else:
                fallback_result = self.selenium.execute_step(fallback_step)

            if fallback_result.get("success"):
                result = fallback_result
                print(f"[Handler] ✅ Full XPath fallback succeeded!")
                result["used_full_xpath"] = True
                result["effective_selector"] = full_xpath
            else:
                print(f"[Handler] ❌ Full XPath fallback also failed: {fallback_result.get('error', 'unknown')}")
                # Keep original error as it's usually more meaningful
                result["error"] = f"Primary selector failed: {original_error} | Retry with full_xpath also failed: {fallback_result.get('error', 'unknown')}"
        else:
            # DEBUG: Why fallback wasn't tried
            if not result.get("success"):
                print(f"[Handler] ❌ Step failed but fallback NOT attempted because:")
                if not step.get("full_xpath"):
                    print(f"[Handler]    - No full_xpath in step")
                if not is_locator_error:
                    print(f"[Handler]    - Not a locator error (content mismatch - fallback won't help)")
        # Wait as specified
        if wait_seconds:
            time.sleep(wait_seconds)

        # Add step_index to result
        result["step_index"] = step_index
        result["executed_step"] = step

        if not result.get("success"):
            result["failed_step"] = step

        return result

    def _handle_fill_autocomplete(self, session_id: int, step: Dict) -> Dict:
        selector = step.get("selector", "")
        value = step.get("value", "a")

        initial_char = value if value else 'a'
        chars_to_try = [initial_char] + [c for c in ['a', 'e', 'i', 'o', 'u', 's', 't', 'n', 'r', '1'] if
                                         c != initial_char]

        for char in chars_to_try:
            # Call selenium to type char
            step_copy = step.copy()
            step_copy["value"] = char
            result = self.selenium.execute_step(step_copy)

            if not result.get("success"):
                return result

            # Take screenshot
            screenshot_result = self.selenium.capture_screenshot(save_to_folder=False)
            screenshot_base64 = screenshot_result.get("screenshot", "")

            # Ask AI if dropdown visible
            if not self.api_client:
                # No API client - assume success on first try
                result["actual_value"] = char
                return result

            ai_result = self.api_client.field_assist_query(
                session_id=str(session_id),
                screenshot_base64=screenshot_base64,
                step=step,
                query_type="dropdown_visible"
            )

            if ai_result.get("success") and ai_result.get("has_valid_options"):
                result["actual_value"] = char
                return result

        return {"success": False, "error": "No autocomplete suggestions after trying all characters"}

    def _handle_screenshot(self, session_id: int, payload: Dict) -> Dict:
        """
        Capture screenshot of current page.
        
        Payload:
            scenario: Description of when screenshot was taken
            encode_base64: Return as base64 string
        """
        scenario = payload.get("scenario", "")
        encode_base64 = payload.get("encode_base64", True)
        
        try:
            # Capture screenshot
            screenshot_bytes = self.selenium.driver.get_screenshot_as_png()
            
            if encode_base64:
                screenshot_data = base64.b64encode(screenshot_bytes).decode('utf-8')
            else:
                screenshot_data = screenshot_bytes
            
            return {
                "success": True,
                "scenario": scenario,
                "screenshot_base64": screenshot_data if encode_base64 else None,
                "screenshot_bytes": screenshot_bytes if not encode_base64 else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Screenshot failed: {e}"
            }
    
    def _handle_navigate(self, session_id: int, payload: Dict) -> Dict:
        """
        Navigate to a URL.
        
        Payload:
            url: URL to navigate to
        """
        url = payload.get("url")
        
        if not url:
            return {
                "success": False,
                "error": "No URL provided"
            }
        
        try:
            self.selenium.navigate_to_url(url)
            time.sleep(1)  # Wait for page load
            
            return {
                "success": True,
                "current_url": self.selenium.driver.current_url
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Navigation failed: {e}"
            }
    
    def _handle_close(self, session_id: int, payload: Dict) -> Dict:
        """
        Close browser and clean up session.
        """
        try:

            # Skip if already closed (handles late/duplicate close tasks)
            if int(session_id) in self.closed_sessions:
                print(f"[DEBUG] Session {session_id} already closed, skipping")
                return {"success": True, "skipped": True, "reason": "already_closed"}


            # Send bulk logs to server if requested
            if payload.get("complete_logging") and self.activity_logger:
                print(f"[DEBUG] complete_logging=True, calling activity_logger.complete()")
                print(f"[DEBUG] session_active={self.activity_logger.session_active}")
                self.activity_logger.complete()
                print(f"[DEBUG] activity_logger.complete() finished")

            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            self.closed_sessions.add(int(session_id))
            
            # Only close if no other active sessions
            if not self.active_sessions:
                self.selenium.close_browser()

            # new fix
            # Clear any stale sessions and close browser
            #self.active_sessions.clear()
            #self.selenium.close_browser()
            
            return {
                "success": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Close failed: {e}"
            }

    def _handle_log_bug(self, session_id: int, payload: Dict) -> Dict:
        """
        Log a bug with screenshot.
        Captures screenshot and displays message in Agent Web UI.

        Payload:
            log_message: The bug message to display
            log_level: 'info', 'warning', 'error' (default: 'error')
            screenshot: True to capture screenshot
            bug_type: Type for filename (e.g., 'ui_issue', 'real_bug_alert')
        """
        bug_description = payload.get("bug_description", "Bug detected")
        bug_type = payload.get("bug_type", "bug")

        # Build log message with appropriate prefix
        if "ui_issue" in bug_type:
            log_message = f"🐛 UI Issue: {bug_description}"
        else:
            log_message = f"🐛 Real bug: {bug_description}"

        log_level = payload.get("log_level", "error")
        should_screenshot = payload.get("screenshot", False)
        bug_type = payload.get("bug_type", "bug")

        screenshot_filename = None

        try:
            # Capture screenshot if requested
            if should_screenshot:
                screenshot_filename = self._capture_bug_screenshot(session_id, bug_type)
                if screenshot_filename:
                    log_message += f" [Screenshot: {screenshot_filename}]"

            # Display in Agent Web UI
            if self.activity_logger:
                if log_level == "error":
                    self.activity_logger.error(log_message)
                elif log_level == "warning":
                    self.activity_logger.warning(log_message)
                else:
                    self.activity_logger.info(log_message)

            return {
                "success": True,
                "screenshot_filename": screenshot_filename
            }

        except Exception as e:
            logger.error(f"[FormMapper] Log bug failed: {e}")
            return {
                "success": False,
                "error": f"Log bug failed: {e}"
            }

    def _capture_bug_screenshot(self, session_id: int, bug_type: str) -> str:
        """
        Capture screenshot for a bug and save locally.
        Returns filename if successful, None otherwise.
        """
        try:
            import os
            from datetime import datetime

            # Capture screenshot
            screenshot_result = self.selenium.capture_screenshot(
                scenario_description=bug_type,
                save_to_folder=False
            )
            if not screenshot_result.get("success"):
                logger.warning(f"[FormMapper] Screenshot capture failed: {screenshot_result.get('error')}")
                return None

            screenshot_b64 = screenshot_result.get("screenshot", "")
            if not screenshot_b64:
                return None

            screenshot_bytes = base64.b64decode(screenshot_b64)

            # Save to mapping subfolder
            screenshot_folder = getattr(self.selenium, 'screenshots_path', None)
            if not screenshot_folder:
                logger.warning("[FormMapper] No screenshot_folder configured")
                return None

            mapping_folder = os.path.join(screenshot_folder, "mapping")
            os.makedirs(mapping_folder, exist_ok=True)

            # Filename format: mapping_{bug_type}_{session_id}_{timestamp}.png
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_bug_type = "".join(c if c.isalnum() or c in "_-" else "_" for c in bug_type[:20])
            filename = f"mapping_{safe_bug_type}_{session_id}_{timestamp}.png"
            filepath = os.path.join(mapping_folder, filename)

            with open(filepath, 'wb') as f:
                f.write(screenshot_bytes)

            logger.info(f"[FormMapper] Bug screenshot saved: {filepath}")
            return filename

        except Exception as e:
            logger.error(f"[FormMapper] Bug screenshot failed: {e}")
            return None


    # ========================================================================
    # Step Execution
    # ========================================================================

    def _execute_step(self, step: Dict) -> bool:
        """Execute a single step using agent_selenium."""
        result = self.selenium.execute_step(step)
        print(f"[DEBUG] execute_step result: {result}")
        return result.get("success", False)



        ''' OBSOLETE - agent selenium is now doing this
        action = step.get("action", "")
        selector = step.get("selector", "")
        value = step.get("value", "")
        
        action_handlers = {
            "fill": self._action_fill,
            "click": self._action_click,
            "select": self._action_select,
            "check": self._action_check,
            "uncheck": self._action_uncheck,
            "upload_file": self._action_upload_file,
            "create_file": self._action_create_file,
            "wait": self._action_wait,
            "verify": self._action_verify,
            "scroll": self._action_scroll,
            "hover": self._action_hover,
            "clear": self._action_clear,
            "press_key": self._action_press_key,
            "accept_alert": self._action_accept_alert,
            "dismiss_alert": self._action_dismiss_alert,
            "navigate": self._action_navigate,
            "wait_dom_ready": self._action_wait_dom_ready,
            "verify_clickables": self._action_verify_clickables,
        }
        
        handler = action_handlers.get(action)
        if not handler:
            logger.warning(f"[FormMapper] Unknown action: {action}")
            return False
        
        return handler(selector, value, step)
        '''
    
    def _action_fill(self, selector: str, value: str, step: Dict) -> bool:
        """Fill a text input field."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Fill failed: {e}")
            return False
    
    def _action_click(self, selector: str, value: str, step: Dict) -> bool:
        """Click an element."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            # Scroll into view
            self.selenium.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            time.sleep(0.3)
            
            element.click()
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Click failed: {e}")
            # Try JavaScript click
            try:
                self.selenium.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def _action_select(self, selector: str, value: str, step: Dict) -> bool:
        """Select an option from dropdown."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            from selenium.webdriver.support.ui import Select
            select = Select(element)
            
            # Try by value first
            try:
                select.select_by_value(value)
                return True
            except:
                pass
            
            # Try by visible text
            try:
                select.select_by_visible_text(value)
                return True
            except:
                pass
            
            # Try partial match
            for option in select.options:
                if value.lower() in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"[FormMapper] Select failed: {e}")
            return False
    
    def _action_check(self, selector: str, value: str, step: Dict) -> bool:
        """Check a checkbox."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            if not element.is_selected():
                element.click()
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Check failed: {e}")
            return False
    
    def _action_uncheck(self, selector: str, value: str, step: Dict) -> bool:
        """Uncheck a checkbox."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            if element.is_selected():
                element.click()
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Uncheck failed: {e}")
            return False
    
    def _action_upload_file(self, selector: str, value: str, step: Dict) -> bool:
        """Upload a file."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            # Value should be the file path
            element.send_keys(value)
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Upload failed: {e}")
            return False
    
    def _action_create_file(self, selector: str, value: str, step: Dict) -> bool:
        """Create a test file for upload."""
        file_type = step.get("file_type", "txt")
        filename = step.get("filename", "test_file.txt")
        content = step.get("content", "Test content")
        
        try:
            import os

            # Create file in session-specific folder (for S3 upload on complete)
            if self.selenium and self.selenium.files_path:
                session_id = self.activity_logger.session_id if self.activity_logger else 'unknown'
                files_dir = os.path.join(self.selenium.files_path, str(session_id))
                os.makedirs(files_dir, exist_ok=True)
                filepath = os.path.join(files_dir, filename)
            else:
                # Fallback to temp directory
                import tempfile
                temp_dir = tempfile.gettempdir()
                filepath = os.path.join(temp_dir, filename)
            
            if file_type == "png":
                # Create a simple PNG
                self._create_test_image(filepath, content)
            elif file_type == "pdf":
                # Create a simple PDF
                self._create_test_pdf(filepath, content)
            else:
                # Create text file
                with open(filepath, 'w') as f:
                    f.write(content)
            
            # Store filepath for next upload step
            step["created_filepath"] = filepath
            
            return True
            
        except Exception as e:
            logger.error(f"[FormMapper] Create file failed: {e}")
            return False
    
    def _action_wait(self, selector: str, value: str, step: Dict) -> bool:
        """Wait for element or time."""
        try:
            if selector:
                # Wait for element
                timeout = int(value) / 1000 if value else 5  # Convert ms to seconds
                WebDriverWait(self.selenium.driver, timeout).until(
                    EC.presence_of_element_located(self._parse_selector(selector))
                )
            else:
                # Just wait
                time.sleep(float(value) / 1000 if value else 1)
            
            return True
            
        except TimeoutException:
            logger.warning(f"[FormMapper] Wait timeout for {selector}")
            return False
        except Exception as e:
            logger.error(f"[FormMapper] Wait failed: {e}")
            return False
    
    def _action_verify(self, selector: str, value: str, step: Dict) -> bool:
        """Verify element exists and optionally contains value."""
        element = self._find_element(selector, timeout=5)
        if not element:
            return False
        
        if value:
            try:
                element_text = element.text or element.get_attribute("value") or ""
                if value.lower() not in element_text.lower():
                    logger.warning(f"[FormMapper] Verify failed: expected '{value}' in '{element_text}'")
                    return False
            except:
                pass
        
        return True
    
    def _action_scroll(self, selector: str, value: str, step: Dict) -> bool:
        """Scroll to element or position."""
        if selector:
            element = self._find_element(selector)
            if element:
                self.selenium.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    element
                )
        else:
            # Scroll by pixels
            self.selenium.driver.execute_script(f"window.scrollBy(0, {value or 300});")
        
        return True
    
    def _action_hover(self, selector: str, value: str, step: Dict) -> bool:
        """Hover over element."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.selenium.driver).move_to_element(element).perform()
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Hover failed: {e}")
            return False
    
    def _action_clear(self, selector: str, value: str, step: Dict) -> bool:
        """Clear input field."""
        element = self._find_element(selector)
        if not element:
            return False
        
        try:
            element.clear()
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Clear failed: {e}")
            return False
    
    def _action_press_key(self, selector: str, value: str, step: Dict) -> bool:
        """Press a keyboard key."""
        from selenium.webdriver.common.keys import Keys
        
        key_map = {
            "enter": Keys.ENTER,
            "tab": Keys.TAB,
            "escape": Keys.ESCAPE,
            "backspace": Keys.BACKSPACE,
            "delete": Keys.DELETE,
        }
        
        key = key_map.get(value.lower(), value)
        
        if selector:
            element = self._find_element(selector)
            if element:
                element.send_keys(key)
        else:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.selenium.driver).send_keys(key).perform()
        
        return True
    
    def _action_accept_alert(self, selector: str, value: str, step: Dict) -> bool:
        """Accept alert dialog."""
        try:
            alert = self.selenium.driver.switch_to.alert
            alert.accept()
            return True
        except NoAlertPresentException:
            return True  # No alert is fine
        except Exception as e:
            logger.error(f"[FormMapper] Accept alert failed: {e}")
            return False
    
    def _action_dismiss_alert(self, selector: str, value: str, step: Dict) -> bool:
        """Dismiss alert dialog."""
        try:
            alert = self.selenium.driver.switch_to.alert
            alert.dismiss()
            return True
        except NoAlertPresentException:
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Dismiss alert failed: {e}")
            return False
    
    # ========================================================================
    # NEW Handlers - Required by Distributed Orchestrator
    # ========================================================================
    
    def _handle_get_screenshot(self, session_id: int, payload: Dict) -> Dict:
        """
        Get screenshot with base64 encoding.
        Used by orchestrator for UI verification.
        
        Payload:
            scenario: Description of when screenshot was taken
        """
        scenario = payload.get("scenario", "")

        try:
            screenshot_result = self.selenium.capture_screenshot(scenario_description=scenario, save_to_folder=False)

            #### FOR DEBUG ####
            #self.selenium.capture_screenshot("_handle_get_screenshot_debug")

            if not screenshot_result.get("success"):
                raise Exception(screenshot_result.get("error", "Screenshot failed"))

            return {
                "success": True,
                "scenario": scenario,
                "screenshot_base64": screenshot_result.get("screenshot", "")
            }
            
        except Exception as e:
            logger.error(f"[FormMapper] Get screenshot failed: {e}")
            return {
                "success": False,
                "error": f"Screenshot failed: {e}"
            }
    
    def _handle_extract_dom_for_recovery(self, session_id: int, payload: Dict) -> Dict:
        """
        Extract DOM and screenshot for step failure recovery.
        Called when a step fails and AI needs fresh DOM + screenshot.
        
        Payload:
            capture_screenshot: Whether to capture screenshot
            save_screenshot: Whether to save screenshot to file
            scenario_description: Description for screenshot filename
        """
        capture_screenshot = payload.get("capture_screenshot", True)
        save_screenshot = payload.get("save_screenshot", False)
        scenario_description = payload.get("scenario_description", "recovery")
        
        try:
            # Extract DOM
            dom_result = self.selenium.extract_dom()
            dom_html = dom_result.get("dom_html", "") if dom_result.get("success") else ""
            
            result = {
                "success": True,
                "dom_html": dom_html,
                "dom_length": len(dom_html) if dom_html else 0
            }
            
            # Capture screenshot if requested
            if capture_screenshot:
                try:
                    screenshot_result = self.selenium.capture_screenshot(scenario_description=scenario_description,
                                                                         save_to_folder=False)

                    #### FOR DEBUG ####
                    #self.selenium.capture_screenshot("_handle_extract_dom_for_recovery_debug")

                    screenshot_b64 = screenshot_result.get("screenshot", "") if screenshot_result.get("success") else ""
                    result["screenshot_base64"] = screenshot_b64
                    
                    # Save to file if requested
                    if save_screenshot and hasattr(self.selenium, 'config'):
                        import os
                        from datetime import datetime
                        
                        screenshot_folder = getattr(self.selenium, 'screenshots_path', None)
                        if screenshot_folder:
                            os.makedirs(screenshot_folder, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_scenario = "".join(c if c.isalnum() or c in "_-" else "_" for c in scenario_description)
                            filepath = os.path.join(screenshot_folder, f"{safe_scenario}_{timestamp}.png")
                            
                            screenshot_bytes = base64.b64decode(screenshot_b64)
                            with open(filepath, 'wb') as f:
                                f.write(screenshot_bytes)
                            
                            result["screenshot_path"] = filepath
                            logger.info(f"[FormMapper] Screenshot saved: {filepath}")
                            
                except Exception as e:
                    logger.warning(f"[FormMapper] Screenshot capture failed: {e}")
                    result["screenshot_error"] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"[FormMapper] Extract DOM for recovery failed: {e}")
            return {
                "success": False,
                "error": f"DOM extraction failed: {e}"
            }
    
    def _handle_extract_dom_for_alert(self, session_id: int, payload: Dict) -> Dict:
        """
        Extract DOM after alert detected.
        Called when an alert/validation error was detected and AI needs fresh DOM.
        
        Payload:
            alert_type: Type of alert detected
            alert_text: Text from the alert
        """
        alert_type = payload.get("alert_type", "unknown")
        alert_text = payload.get("alert_text", "")
        
        logger.info(f"[FormMapper] Extracting DOM after alert: {alert_type}")
        
        try:
            # Extract DOM
            dom_result = self.selenium.extract_dom()
            dom_html = dom_result.get("dom_html", "") if dom_result.get("success") else ""
            
            # Also capture screenshot for context
            screenshot_b64 = None
            try:
                screenshot_result = self.selenium.capture_screenshot(scenario_description="alert_context",
                                                                     save_to_folder=False)
                screenshot_b64 = screenshot_result.get("screenshot", "") if screenshot_result.get("success") else None
            except:
                pass
            
            # Gather any validation error info from the page
            gathered_error_info = self._gather_error_info()
            
            return {
                "success": True,
                "dom_html": dom_html,
                "dom_length": len(dom_html) if dom_html else 0,
                "screenshot_base64": screenshot_b64,
                "alert_type": alert_type,
                "alert_text": alert_text,
                "gathered_error_info": gathered_error_info
            }
            
        except Exception as e:
            logger.error(f"[FormMapper] Extract DOM for alert failed: {e}")
            return {
                "success": False,
                "error": f"DOM extraction failed: {e}"
            }
    
    def _handle_save_screenshot_and_log(self, session_id: int, payload: Dict) -> Dict:
        """
        Save screenshot to file and log UI issue.
        Called when UI verification detects an issue.
        
        Payload:
            ui_issue: Description of the UI issue detected
            scenario: Screenshot scenario description
        """
        ui_issue = payload.get("ui_issue", "")
        scenario = payload.get("scenario", "ui_issue")
        
        try:
            # Capture screenshot
            screenshot_result = self.selenium.capture_screenshot(scenario_description=scenario, save_to_folder=False)
            if not screenshot_result.get("success"):
                raise Exception(screenshot_result.get("error", "Screenshot failed"))
            screenshot_b64 = screenshot_result.get("screenshot", "")
            screenshot_bytes = base64.b64decode(screenshot_b64)
            
            # Save to file
            filepath = None
            if hasattr(self.selenium, 'config'):
                import os
                from datetime import datetime
                
                screenshot_folder = getattr(self.selenium, 'screenshots_path', None)
                if screenshot_folder:
                    os.makedirs(screenshot_folder, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_scenario = "".join(c if c.isalnum() or c in "_-" else "_" for c in scenario)
                    filepath = os.path.join(screenshot_folder, f"ui_issue_{safe_scenario}_{timestamp}.png")
                    
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_bytes)
                    
                    logger.info(f"[FormMapper] UI issue screenshot saved: {filepath}")
            
            # Log the UI issue
            logger.warning(f"[FormMapper] UI Issue detected: {ui_issue}")
            
            return {
                "success": True,
                "ui_issue": ui_issue,
                "screenshot_path": filepath,
                "screenshot_base64": screenshot_b64
            }
            
        except Exception as e:
            logger.error(f"[FormMapper] Save screenshot and log failed: {e}")
            return {
                "success": False,
                "error": f"Save screenshot failed: {e}"
            }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _find_element(self, selector: str, timeout: int = 10):
        """Find element by selector (CSS or XPath)."""
        try:
            by, locator = self._parse_selector(selector)
            
            element = WebDriverWait(self.selenium.driver, timeout).until(
                EC.presence_of_element_located((by, locator))
            )
            
            return element
            
        except TimeoutException:
            logger.warning(f"[FormMapper] Element not found: {selector}")
            return None
        except Exception as e:
            logger.error(f"[FormMapper] Find element error: {e}")
            return None
    
    def _parse_selector(self, selector: str) -> tuple:
        """Parse selector string to (By, locator) tuple."""
        if selector.startswith("xpath="):
            return (By.XPATH, selector[6:])
        elif selector.startswith("//") or selector.startswith("(//"):
            return (By.XPATH, selector)
        else:
            return (By.CSS_SELECTOR, selector)
    
    def _check_and_handle_alert(self) -> Dict:
        """Check for and handle JavaScript alerts."""
        try:
            alert = WebDriverWait(self.selenium.driver, 0.5).until(
                EC.alert_is_present()
            )
            
            alert_text = alert.text

            # Capture screenshot BEFORE accepting alert (so AI can see the alert dialog)
            screenshot_b64 = None
            try:
                screenshot_result = self.selenium.capture_screenshot(
                    scenario_description="alert_visible",
                    save_to_folder=False
                )
                if screenshot_result.get("success"):
                    screenshot_b64 = screenshot_result.get("screenshot", "")
                    logger.info(f"[FormMapper] Captured screenshot with alert visible")
            except Exception as e:
                logger.warning(f"[FormMapper] Failed to capture alert screenshot: {e}")

            alert.accept()  # Always accept
            
            logger.info(f"[FormMapper] Alert detected and accepted: {alert_text[:100]}")
            
            return {
                "alert_present": True,
                "alert_type": "alert",
                "alert_text": alert_text,
                "alert_screenshot_base64": screenshot_b64
            }
            
        except TimeoutException:
            return {"alert_present": False}
        except NoAlertPresentException:
            return {"alert_present": False}
        except Exception as e:
            logger.warning(f"[FormMapper] Alert check error: {e}")
            return {"alert_present": False}
    
    def _check_fields_changed(self, old_dom: str, new_dom: str) -> bool:
        """Check if form fields changed between DOMs (simplified)."""
        # Simple heuristic: check if number of input elements changed
        import re
        
        old_inputs = len(re.findall(r'<input[^>]*>', old_dom, re.IGNORECASE))
        new_inputs = len(re.findall(r'<input[^>]*>', new_dom, re.IGNORECASE))
        
        old_selects = len(re.findall(r'<select[^>]*>', old_dom, re.IGNORECASE))
        new_selects = len(re.findall(r'<select[^>]*>', new_dom, re.IGNORECASE))
        
        return (old_inputs != new_inputs) or (old_selects != new_selects)
    
    def _gather_error_info(self) -> Dict:
        """Gather validation error info from DOM."""
        try:
            error_fields = []
            error_messages = []
            
            # Look for common error indicators
            error_selectors = [
                ".error", ".has-error", ".is-invalid", ".field-error",
                "[class*='error']", "[class*='invalid']",
                ".validation-error", ".form-error"
            ]
            
            for selector in error_selectors:
                try:
                    elements = self.selenium.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        text = el.text.strip()
                        if text:
                            error_messages.append(text)
                            
                            # Try to find associated field
                            parent = el.find_element(By.XPATH, "./..")
                            field_input = parent.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                            if field_input:
                                name = field_input[0].get_attribute("name") or field_input[0].get_attribute("id")
                                if name:
                                    error_fields.append(name)
                except:
                    pass
            
            return {
                "error_fields": list(set(error_fields)),
                "error_messages": list(set(error_messages))
            }
            
        except Exception as e:
            logger.warning(f"[FormMapper] Error gathering error info: {e}")
            return {}
    
    def _execute_navigation_step(self, step: Dict):
        """Execute a navigation step (simplified)."""
        action = step.get("action", "click")
        selector = step.get("selector", "")
        
        if action == "click" and selector:
            element = self._find_element(selector, timeout=5)
            if element:
                element.click()
                time.sleep(0.5)
    
    def _create_test_image(self, filepath: str, content: str):
        """Create a simple test PNG image."""
        try:
            from PIL import Image, ImageDraw
            
            img = Image.new('RGB', (200, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), content[:30], fill='black')
            img.save(filepath, 'PNG')
        except ImportError:
            # Fallback: create empty file
            with open(filepath, 'wb') as f:
                # Minimal PNG
                f.write(b'\x89PNG\r\n\x1a\n')
    
    def _create_test_pdf(self, filepath: str, content: str):
        """Create a simple test PDF."""
        try:
            from reportlab.pdfgen import canvas
            
            c = canvas.Canvas(filepath)
            c.drawString(100, 750, content[:50])
            c.save()
        except ImportError:
            # Fallback: create text file with .pdf extension
            with open(filepath, 'w') as f:
                f.write(content)


# ============================================================================
# Integration with main.py
# ============================================================================
# Add to your agent's main.py:
#
# from form_mapper_handler import FormMapperTaskHandler
#
# # Initialize handler
# form_mapper_handler = FormMapperTaskHandler(agent_selenium)
#
# # In your task processing loop:
# if task_type.startswith("form_mapper_") or task_type.startswith("forms_runner_"):
#     result = form_mapper_handler.handle_task(task)
#     # Report result to server
#     report_task_result(result)
# ============================================================================

    def _action_navigate(self, selector: str, value: str, step: Dict) -> bool:
        """Navigate to URL."""
        url = step.get("url") or value
        if not url:
            logger.warning("[FormMapper] Navigate action requires url")
            return False
        try:
            self.selenium.navigate_to_url(url)
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Navigate failed: {e}")
            return False

    def _action_wait_dom_ready(self, selector: str, value: str, step: Dict) -> bool:
        """Wait for DOM to stabilize after page load."""
        import time
        try:
            time.sleep(2)  # Initial wait
            # Wait for page to be ready
            self.selenium.driver.execute_script("return document.readyState") == "complete"
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"[FormMapper] Wait DOM ready failed: {e}")
            return False

    def _action_verify_clickables(self, selector: str, value: str, step: Dict) -> bool:
        """Verify login succeeded by checking for clickable elements."""
        try:
            from selenium.webdriver.common.by import By
            clickables = self.selenium.driver.find_elements(By.CSS_SELECTOR, "a, button, [onclick]")
            visible_clickables = [el for el in clickables if el.is_displayed()]
            if len(visible_clickables) >= 7:
                logger.info(f"[FormMapper] Found {len(visible_clickables)} clickable elements - login verified")
                return True
            else:
                logger.warning(f"[FormMapper] Only {len(visible_clickables)} clickables - login may have failed")
                return False
        except Exception as e:
            logger.error(f"[FormMapper] Verify clickables failed: {e}")
            return False
