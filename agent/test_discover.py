#!/usr/bin/env python3
"""Quick test for form page discovery"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from crawler import FormPagesCrawler, FormPagesAPIClient

# Config
API_URL = "http://localhost:8001"
AGENT_TOKEN = "test-token"

# Task params (from API response)
params = {
    "crawl_session_id": 1,
    "network_url": "https://opensource-demo.orangehrmlive.com",
    "login_url": "https://opensource-demo.orangehrmlive.com",
    "login_username": "Admin",
    "login_password": "admin123",
    "project_name": "E-commerce Testing",
    "company_id": 1,
    "product_id": 1,
    "project_id": 1,
    "network_id": 2,
    "user_id": 1,
    "max_depth": 20,
    "max_form_pages": 10,
    "headless": False,
    "slow_mode": True
}

print("🚀 Starting form discovery test...")

# Create API client
api_client = FormPagesAPIClient(
    api_url=API_URL,
    agent_token=AGENT_TOKEN,
    company_id=params["company_id"],
    product_id=params["product_id"],
    project_id=params["project_id"],
    network_id=params["network_id"],
    crawl_session_id=params["crawl_session_id"]
)
api_client.max_form_pages = params["max_form_pages"]

# Initialize browser (like agent_selenium.py)
print("🌐 Initializing Chrome browser...")

options = Options()
options.binary_location = '/opt/google/chrome/google-chrome'
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

service = Service('/home/ranlaser/.wdm/drivers/chromedriver/linux64/141.0.7390.122/chromedriver-linux64/chromedriver')
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(40)
print("[WebDriver] ✅ Initialized successfully")

# Navigate to login
print(f"📍 Navigating to: {params['login_url']}")
driver.get(params["login_url"])
time.sleep(3)

# Get login steps from AI
print("🔐 Getting login steps from AI...")
page_html = driver.execute_script("return document.documentElement.outerHTML")
screenshot_b64 = driver.get_screenshot_as_base64()

login_steps = api_client.generate_login_steps(
    page_html=page_html,
    screenshot_base64=screenshot_b64,
    username=params["login_username"],
    password=params["login_password"]
)

print(f"🔐 Executing {len(login_steps)} login steps...")
for step in login_steps:
    action = step.get('action')
    selector = step.get('selector')
    value = step.get('value', '')
    print(f"  → {action}: {selector}")
    
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
print("✅ Login complete!")

# Run crawler
base_url = driver.current_url
print(f"📍 Base URL: {base_url}")
print("🕷️ Starting crawler...")

crawler = FormPagesCrawler(
    driver=driver,
    start_url=base_url,
    base_url=base_url,
    project_name=params["project_name"],
    max_depth=params["max_depth"],
    target_form_pages=[],
    discovery_only=True,
    slow_mode=params["slow_mode"],
    server=api_client,
    username=params["login_username"],
    login_url=params["login_url"],
    agent=None
)

crawler.crawl()

print(f"\n✅ Discovery complete! Found {api_client.new_form_pages_count} forms")
print("Press Enter to close browser...")
input()
driver.quit()
