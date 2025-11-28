#!/usr/bin/env python3
"""
Form Discoverer Agent - Main Entry Point (WEB UI VERSION)
Location: web_services_product/agent/main.py

Runs on customer's network, connects to api-server, executes Selenium automation
Now with web-based UI and system tray icon!

FIXED: Added agent_id and company_id as query parameters to poll-task endpoint
"""

import os
import sys
import time
import logging
import requests
import threading
from typing import Optional, Dict, Any
from pathlib import Path

from agent_config import AgentConfig
from agent_selenium import AgentSelenium
from tray_icon import AgentTrayIcon
from traffic_capture import TrafficCapture
from web_ui.server import start_server
from crawler import FormPagesCrawler, FormPagesAPIClient

def check_first_run():
    """Check if this is first run (no .env file)"""
    env_file = Path('.env')
    return not env_file.exists()


class FormDiscovererAgent:
    """Main agent that connects to the server and coordinates operations"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = AgentConfig(config_file)
        self._setup_logging()
        self.selenium_agent = AgentSelenium(screenshot_folder=self.config.screenshot_folder)
        self.is_running = False
        self.current_task_id = None
        self.heartbeat_thread = None
        self.tray_icon = None
        
        # Initialize traffic capture if enabled
        if getattr(self.config, 'capture_traffic', False):
            traffic_storage = Path(self.config.log_folder) / 'traffic' if self.config.log_folder else None
            self.traffic = TrafficCapture(enabled=True, storage_path=traffic_storage)
            self.logger.info("✓ Browser traffic capture enabled")
        else:
            self.traffic = None
            self.logger.info("✓ Browser traffic capture disabled")
        
        self.logger.info("="*70)
        self.logger.info("Form Discoverer Agent Initialized")
        self.logger.info(f"API URL: {self.config.api_url}")
        self.logger.info(f"Agent ID: {self.config.agent_id}")
        self.logger.info(f"Company ID: {self.config.company_id}")
        self.logger.info(f"User ID: {self.config.user_id}")
        self.logger.info("="*70)
    
    def _setup_logging(self):
        log_dir = getattr(self.config, 'log_folder', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"agent_{time.strftime('%Y%m%d_%H%M%S')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('FormDiscovererAgent')
    
    def connect_to_server(self) -> bool:
        try:
            self.logger.info("Connecting to server...")
            url = f"{self.config.api_url}/api/agent/register"
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
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.logger.info(f"✅ Connected successfully")
                # Update tray icon status
                if self.tray_icon:
                    self.tray_icon.update_status(True)
                return True
            else:
                self.logger.error(f"❌ Failed: HTTP {response.status_code}")
                if self.tray_icon:
                    self.tray_icon.update_status(False)
                return False
        except Exception as e:
            self.logger.error(f"❌ Connection error: {str(e)}")
            if self.tray_icon:
                self.tray_icon.update_status(False)
            return False
    
    def send_heartbeat(self):
        while self.is_running:
            try:
                url = f"{self.config.api_url}/api/agent/heartbeat"
                headers = {"Authorization": f"Bearer {self.config.agent_token}", "Content-Type": "application/json"}
                payload = {
                    "agent_id": self.config.agent_id,
                    "status": "idle" if not self.current_task_id else "busy",
                    "current_task_id": self.current_task_id
                }
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                
                # Update tray icon based on connection
                if self.tray_icon:
                    self.tray_icon.update_status(response.status_code == 200)
                    
            except Exception as e:
                self.logger.warning(f"Heartbeat error: {str(e)}")
                if self.tray_icon:
                    self.tray_icon.update_status(False)
            time.sleep(30)
    
    def poll_for_tasks(self):
        self.logger.info("📡 Polling for tasks...")
        consecutive_errors = 0
        
        while self.is_running:
            try:
                # FIXED: Add agent_id and company_id as query parameters
                url = f"{self.config.api_url}/api/agent/poll-task?agent_id={self.config.agent_id}&company_id={self.config.company_id}"
                headers = {"Authorization": f"Bearer {self.config.agent_token}"}
                response = requests.get(url, headers=headers, timeout=35)
                
                if response.status_code == 200:
                    task = response.json()
                    consecutive_errors = 0
                    if task and task.get('task_id'):
                        self.logger.info(f"📥 Received task: {task.get('task_id')}")
                        self.execute_task(task)
                elif response.status_code == 204:
                    consecutive_errors = 0
                    time.sleep(1)
                else:
                    consecutive_errors += 1
                    self.logger.error(f"Poll returned status code: {response.status_code}")
                    time.sleep(5)
            except requests.exceptions.Timeout:
                consecutive_errors = 0
                continue
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Poll error: {str(e)}")
                time.sleep(5)
            
            if consecutive_errors >= 5:
                self.logger.error("Too many errors, stopping")
                self.is_running = False
                break
    
    def execute_task(self, task: Dict[str, Any]):
        task_id = task.get('task_id')
        task_type = task.get('task_type')
        params = task.get('parameters', {})
        self.current_task_id = task_id
        
        try:
            self.logger.info(f"🔧 Executing: {task_type}")
            self._update_task_status(task_id, "running", "Task started")
            
            # Clear previous traffic session if capture enabled
            if self.traffic:
                self.traffic.clear_session()
            
            if task_type == "execute_test":
                result = self._handle_execute_test(params)
            elif task_type == "navigate_url":
                result = self._handle_navigate_url(params)
            elif task_type == "extract_dom":
                result = self._handle_extract_dom(params)
            elif task_type == "execute_steps":
                result = self._handle_execute_steps(params)
            elif task_type == "discover_form_pages":
                result = self._handle_discover_form_pages(params)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            # Log traffic if server requested debugging
            if self.traffic and task.get('debug_traffic'):
                self.logger.info("Server requested traffic dump for debugging")
                self.traffic.print_traffic_for_debugging(
                    url_pattern=task.get('debug_url_pattern')
                )
            
            if result.get('success'):
                self._update_task_status(task_id, "completed", "Success", result)
                self.logger.info(f"✅ Task completed")
            else:
                self._update_task_status(task_id, "failed", result.get('error'), result)
                self.logger.error(f"❌ Task failed")
        except Exception as e:
            self.logger.error(f"❌ Error: {str(e)}")
            self._update_task_status(task_id, "failed", str(e))
        finally:
            self.current_task_id = None
    
    def _update_task_status(self, task_id: str, status: str, message: str, result: Optional[Dict] = None):
        try:
            url = f"{self.config.api_url}/api/agent/task-status"
            headers = {"Authorization": f"Bearer {self.config.agent_token}", "Content-Type": "application/json"}
            payload = {"task_id": task_id, "status": status, "message": message, "result": result}
            requests.post(url, json=payload, headers=headers, timeout=30)
        except Exception as e:
            self.logger.error(f"Status update error: {str(e)}")
    
    def _handle_navigate_url(self, params: Dict) -> Dict:
        url = params.get('url')
        if not url:
            return {"success": False, "error": "URL required"}
        if not self.selenium_agent.driver:
            self.selenium_agent.initialize_browser(browser_type=params.get('browser', 'chrome'), headless=params.get('headless', False))
        return self.selenium_agent.navigate_to_url(url)
    
    def _handle_extract_dom(self, params: Dict) -> Dict:
        if not self.selenium_agent.driver:
            return {"success": False, "error": "Browser not initialized"}
        return self.selenium_agent.extract_dom()
    
    def _handle_execute_steps(self, params: Dict) -> Dict:
        steps = params.get('steps', [])
        if not steps:
            return {"success": False, "error": "No steps"}
        if not self.selenium_agent.driver:
            return {"success": False, "error": "Browser not initialized"}
        
        results = []
        for step in steps:
            result = self.selenium_agent.execute_step(step)
            results.append(result)
            if not result.get('success') and params.get('stop_on_failure', True):
                break
        
        return {
            "success": all(r.get('success', False) for r in results),
            "steps_executed": len(results),
            "results": results
        }
    
    def _handle_execute_test(self, params: Dict) -> Dict:
        test_url = params.get('test_url')
        test_steps = params.get('test_steps', [])
        
        if not test_url:
            return {"success": False, "error": "test_url required"}
        if not test_steps:
            return {"success": False, "error": "test_steps required"}
        
        if not self.selenium_agent.driver:
            self.selenium_agent.initialize_browser(
                browser_type=params.get('browser', 'chrome'),
                headless=params.get('headless', False)
            )
        
        nav_result = self.selenium_agent.navigate_to_url(test_url)
        if not nav_result.get('success'):
            return nav_result
        
        return self._handle_execute_steps({'steps': test_steps})

    def _handle_discover_form_pages(self, params: Dict) -> Dict:
        """Handle form page discovery task"""
        self.logger.info("🔍 Starting form page discovery...")

        crawl_session_id = params.get('crawl_session_id')
        network_url = params.get('network_url')
        login_url = params.get('login_url', network_url)
        login_username = params.get('login_username')
        login_password = params.get('login_password')
        project_name = params.get('project_name', 'default')
        max_depth = params.get('max_depth', 20)
        max_form_pages = params.get('max_form_pages')
        headless = params.get('headless', False)
        slow_mode = params.get('slow_mode', True)

        api_client = FormPagesAPIClient(
            api_url=self.config.api_url,
            agent_token=self.config.agent_token,
            company_id=params.get('company_id'),
            product_id=params.get('product_id'),
            project_id=params.get('project_id'),
            network_id=params.get('network_id'),
            crawl_session_id=crawl_session_id
        )
        api_client.max_form_pages = max_form_pages

        api_client.update_crawl_session(status='running')

        try:
            # Always close existing browser and create fresh session
            # This prevents "invalid session id" errors from stale/closed sessions
            if self.selenium_agent.driver:
                self.logger.info("Closing existing browser session...")
                try:
                    self.selenium_agent.close_browser()
                except Exception as e:
                    self.logger.warning(f"Error closing old browser: {e}")
            
            # Always create a fresh browser for each discovery
            self.selenium_agent.initialize_browser(
                browser_type=params.get('browser', 'chrome'),
                headless=headless
            )

            driver = self.selenium_agent.driver
            driver.get(login_url)
            time.sleep(2)

            if login_username and login_password:
                self.logger.info(f"Logging in as: {login_username}")
                page_html = driver.execute_script("return document.documentElement.outerHTML")
                screenshot_b64 = driver.get_screenshot_as_base64()

                login_steps = api_client.generate_login_steps(
                    page_html=page_html,
                    screenshot_base64=screenshot_b64,
                    username=login_username,
                    password=login_password
                )

                from selenium.webdriver.common.by import By
                for step in login_steps:
                    action = step.get('action')
                    selector = step.get('selector')
                    value = step.get('value', '')

                    if action == 'fill':
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                        element.clear()
                        element.send_keys(value)
                        time.sleep(0.3)
                    elif action == 'click':
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                        element.click()
                        time.sleep(0.5)
                    elif action in ('wait_dom_ready', 'verify_clickables'):
                        time.sleep(1)

                time.sleep(2)

            base_url = driver.current_url

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
                agent=None
            )

            crawler.crawl()

            api_client.update_crawl_session(
                status='completed',
                forms_found=api_client.new_form_pages_count
            )

            return {
                "success": True,
                "forms_found": api_client.new_form_pages_count,
                "crawl_session_id": crawl_session_id
            }

        except Exception as e:
            self.logger.error(f"Form discovery failed: {e}")
            api_client.update_crawl_session(status='failed', error_message=str(e))
            return {"success": False, "error": str(e)}
        
        finally:
            # Always close browser after discovery (success or failure)
            # This ensures clean state for next task
            if self.selenium_agent.driver:
                self.logger.info("Closing browser after discovery...")
                try:
                    self.selenium_agent.close_browser()
                except Exception as e:
                    self.logger.warning(f"Error closing browser: {e}")


    def start(self):
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
