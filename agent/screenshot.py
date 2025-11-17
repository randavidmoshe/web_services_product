"""
Screenshot capture and upload module for the agent
Integrates with Selenium to capture screenshots during crawling
"""

import requests
from selenium import webdriver
from typing import Optional
import os

class ScreenshotManager:
    """Manages screenshot capture and upload to API server"""
    
    def __init__(self, api_url: str, agent_token: str):
        """
        Initialize screenshot manager
        
        Args:
            api_url: API server URL (e.g., http://localhost:8000)
            agent_token: Agent authentication token
        """
        self.api_url = api_url
        self.agent_token = agent_token
        self.screenshot_endpoint = f"{api_url}/api/screenshots/upload"
    
    def capture_and_upload(
        self,
        driver: webdriver.Chrome,
        company_id: int,
        crawl_session_id: int,
        image_type: str,
        form_page_id: Optional[int] = None,
        product_id: Optional[int] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> dict:
        """
        Capture screenshot from Selenium driver and upload to API
        
        Args:
            driver: Selenium WebDriver instance
            company_id: Company ID
            crawl_session_id: Current crawl session ID
            image_type: Type of screenshot (initial_load, after_interaction, error, etc)
            form_page_id: Optional form page ID
            product_id: Optional product ID
            description: Optional description
            user_id: Optional user ID
        
        Returns:
            dict with screenshot metadata (id, url, etc)
        """
        
        # Capture screenshot as PNG bytes
        screenshot_bytes = driver.get_screenshot_as_png()
        
        # Generate filename
        filename = f"{image_type}_{crawl_session_id}.png"
        
        # Prepare multipart form data
        files = {
            'image': (filename, screenshot_bytes, 'image/png')
        }
        
        data = {
            'company_id': company_id,
            'crawl_session_id': crawl_session_id,
            'image_type': image_type,
        }
        
        if form_page_id:
            data['form_page_id'] = form_page_id
        if product_id:
            data['product_id'] = product_id
        if description:
            data['description'] = description
        if user_id:
            data['user_id'] = user_id
        
        # Upload to API
        response = requests.post(
            self.screenshot_endpoint,
            files=files,
            data=data,
            headers={'Authorization': f'Bearer {self.agent_token}'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to upload screenshot: {response.status_code} - {response.text}")
    
    def capture_initial_page(
        self,
        driver: webdriver.Chrome,
        company_id: int,
        crawl_session_id: int,
        form_page_id: int,
        url: str
    ) -> dict:
        """
        Capture initial page load screenshot
        
        Args:
            driver: Selenium WebDriver
            company_id: Company ID
            crawl_session_id: Crawl session ID
            form_page_id: Form page ID
            url: Page URL being captured
        
        Returns:
            Screenshot metadata
        """
        return self.capture_and_upload(
            driver=driver,
            company_id=company_id,
            crawl_session_id=crawl_session_id,
            image_type='initial_load',
            form_page_id=form_page_id,
            description=f"Initial page load: {url}"
        )
    
    def capture_after_interaction(
        self,
        driver: webdriver.Chrome,
        company_id: int,
        crawl_session_id: int,
        form_page_id: int,
        action: str
    ) -> dict:
        """
        Capture screenshot after user interaction
        
        Args:
            driver: Selenium WebDriver
            company_id: Company ID
            crawl_session_id: Crawl session ID
            form_page_id: Form page ID
            action: Description of action performed
        
        Returns:
            Screenshot metadata
        """
        return self.capture_and_upload(
            driver=driver,
            company_id=company_id,
            crawl_session_id=crawl_session_id,
            image_type='after_interaction',
            form_page_id=form_page_id,
            description=f"After: {action}"
        )
    
    def capture_error(
        self,
        driver: webdriver.Chrome,
        company_id: int,
        crawl_session_id: int,
        error_message: str,
        form_page_id: Optional[int] = None
    ) -> dict:
        """
        Capture screenshot when error occurs
        
        Args:
            driver: Selenium WebDriver
            company_id: Company ID
            crawl_session_id: Crawl session ID
            error_message: Error message/description
            form_page_id: Optional form page ID
        
        Returns:
            Screenshot metadata
        """
        return self.capture_and_upload(
            driver=driver,
            company_id=company_id,
            crawl_session_id=crawl_session_id,
            image_type='error',
            form_page_id=form_page_id,
            description=f"Error: {error_message}"
        )
    
    def capture_form_filled(
        self,
        driver: webdriver.Chrome,
        company_id: int,
        crawl_session_id: int,
        form_page_id: int
    ) -> dict:
        """
        Capture screenshot of form after filling fields
        
        Args:
            driver: Selenium WebDriver
            company_id: Company ID
            crawl_session_id: Crawl session ID
            form_page_id: Form page ID
        
        Returns:
            Screenshot metadata
        """
        return self.capture_and_upload(
            driver=driver,
            company_id=company_id,
            crawl_session_id=crawl_session_id,
            image_type='form_filled',
            form_page_id=form_page_id,
            description="Form filled with test data"
        )


# Example usage in your crawler code:
"""
from screenshot import ScreenshotManager

# Initialize
screenshot_mgr = ScreenshotManager(
    api_url="http://localhost:8000",
    agent_token="your-agent-token"
)

# During crawling
driver = webdriver.Chrome()
driver.get("https://example.com/contact")

# Capture initial load
screenshot_mgr.capture_initial_page(
    driver=driver,
    company_id=1,
    crawl_session_id=123,
    form_page_id=456,
    url="https://example.com/contact"
)

# Fill form...
# Capture after filling
screenshot_mgr.capture_form_filled(
    driver=driver,
    company_id=1,
    crawl_session_id=123,
    form_page_id=456
)

# Click submit...
# Capture after interaction
screenshot_mgr.capture_after_interaction(
    driver=driver,
    company_id=1,
    crawl_session_id=123,
    form_page_id=456,
    action="Clicked submit button"
)

# If error occurs
try:
    # ... crawling code ...
except Exception as e:
    screenshot_mgr.capture_error(
        driver=driver,
        company_id=1,
        crawl_session_id=123,
        error_message=str(e),
        form_page_id=456
    )
"""
