# chrome_manager.py
# Robust cross-platform Chrome/ChromeDriver management
# Handles version detection, driver download, permissions, and profile isolation

import os
import stat
import tempfile
import platform
import subprocess
import re
import shutil
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class ChromeManager:
    """
    Robust Chrome browser management for Selenium automation.
    
    Features:
    - Detects installed Chrome version on Windows/Mac/Linux
    - Downloads exact matching ChromeDriver version
    - Auto-fixes permissions (Linux/Mac)
    - Uses isolated profile (never interferes with user's Chrome)
    - Multiple fallback methods
    - Cache management
    """
    
    def __init__(self):
        self.system = platform.system()
        self.chrome_version = None
        self.driver_path = None
        
    def get_installed_chrome_version(self) -> Optional[str]:
        """
        Detect installed Chrome version on any OS.
        Returns version string like "120.0.6099.109" or None if not found.
        """
        try:
            if self.system == 'Windows':
                return self._get_chrome_version_windows()
            elif self.system == 'Darwin':  # macOS
                return self._get_chrome_version_mac()
            else:  # Linux
                return self._get_chrome_version_linux()
        except Exception as e:
            print(f"[ChromeManager] Could not detect Chrome version: {e}")
            return None
    
    def _get_chrome_version_windows(self) -> Optional[str]:
        """Get Chrome version on Windows"""
        # Method 1: Registry
        try:
            import winreg
            paths = [
                r"SOFTWARE\Google\Chrome\BLBeacon",
                r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon",
            ]
            for path in paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
                    version, _ = winreg.QueryValueEx(key, "version")
                    winreg.CloseKey(key)
                    if version:
                        print(f"[ChromeManager] Chrome version (registry): {version}")
                        return version
                except:
                    continue
        except ImportError:
            pass
        
        # Method 2: PowerShell
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 "(Get-Item 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe').VersionInfo.FileVersion"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip()
                print(f"[ChromeManager] Chrome version (powershell): {version}")
                return version
        except:
            pass
        
        # Method 3: WMIC
        try:
            result = subprocess.run(
                ['wmic', 'datafile', 'where', 
                 'name="C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"', 
                 'get', 'Version', '/value'],
                capture_output=True, text=True, timeout=10
            )
            match = re.search(r'Version=(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                version = match.group(1)
                print(f"[ChromeManager] Chrome version (wmic): {version}")
                return version
        except:
            pass
        
        return None
    
    def _get_chrome_version_mac(self) -> Optional[str]:
        """Get Chrome version on macOS"""
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    result = subprocess.run(
                        [chrome_path, '--version'],
                        capture_output=True, text=True, timeout=10
                    )
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        version = match.group(1)
                        print(f"[ChromeManager] Chrome version: {version}")
                        return version
                except:
                    continue
        
        return None
    
    def _get_chrome_version_linux(self) -> Optional[str]:
        """Get Chrome version on Linux"""
        chrome_commands = [
            ['google-chrome', '--version'],
            ['google-chrome-stable', '--version'],
            ['chromium', '--version'],
            ['chromium-browser', '--version'],
        ]
        
        for cmd in chrome_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    version = match.group(1)
                    print(f"[ChromeManager] Chrome version: {version}")
                    return version
            except:
                continue
        
        return None
    
    def get_major_version(self, full_version: str) -> str:
        """Extract major version from full version string"""
        if full_version:
            return full_version.split('.')[0]
        return None
    
    def fix_permissions(self, driver_path: str) -> bool:
        """Ensure chromedriver has execute permissions (Linux/Mac only)"""
        try:
            if self.system == 'Windows':
                return True  # Windows doesn't need execute permissions
            
            if os.path.exists(driver_path) and not os.access(driver_path, os.X_OK):
                current_mode = os.stat(driver_path).st_mode
                os.chmod(driver_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                print(f"[ChromeManager] Fixed permissions for: {driver_path}")
            return True
        except Exception as e:
            print(f"[ChromeManager] Could not fix permissions: {e}")
            return False
    
    def find_chromedriver_in_dir(self, driver_dir: str) -> Optional[str]:
        """Find chromedriver executable in directory"""
        try:
            for filename in os.listdir(driver_dir):
                if filename in ('chromedriver', 'chromedriver.exe'):
                    return os.path.join(driver_dir, filename)
        except:
            pass
        return None
    
    def get_common_chromedriver_paths(self) -> list:
        """Get common chromedriver paths based on OS"""
        paths = []
        
        if self.system == 'Windows':
            local_app = os.environ.get('LOCALAPPDATA', '')
            program_files = os.environ.get('PROGRAMFILES', '')
            program_files_x86 = os.environ.get('PROGRAMFILES(X86)', '')
            paths = [
                os.path.join(local_app, 'Programs', 'chromedriver.exe'),
                os.path.join(program_files, 'chromedriver', 'chromedriver.exe'),
                os.path.join(program_files_x86, 'chromedriver', 'chromedriver.exe'),
            ]
        elif self.system == 'Darwin':  # macOS
            paths = [
                '/usr/local/bin/chromedriver',
                '/opt/homebrew/bin/chromedriver',
                os.path.expanduser('~/bin/chromedriver'),
            ]
        else:  # Linux
            paths = [
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
                os.path.expanduser('~/.local/bin/chromedriver'),
                '/snap/bin/chromium.chromedriver',
            ]
        
        # Also search in .wdm directory (all platforms)
        wdm_dir = os.path.expanduser('~/.wdm/drivers/chromedriver')
        if os.path.exists(wdm_dir):
            for root, dirs, files in os.walk(wdm_dir):
                for f in files:
                    if f in ('chromedriver', 'chromedriver.exe'):
                        paths.append(os.path.join(root, f))
        
        return paths
    
    def clear_driver_cache(self):
        """Clear ChromeDriver cache"""
        try:
            wdm_cache = os.path.expanduser('~/.wdm')
            if os.path.exists(wdm_cache):
                shutil.rmtree(wdm_cache, ignore_errors=True)
                print("[ChromeManager] Cleared ChromeDriver cache")
                return True
        except Exception as e:
            print(f"[ChromeManager] Could not clear cache: {e}")
        return False
    
    def get_isolated_profile_dir(self) -> str:
        """Get isolated Chrome profile directory (never interferes with user's Chrome)"""
        profile_dir = os.path.join(tempfile.gettempdir(), "quattera-selenium-profile")
        os.makedirs(profile_dir, exist_ok=True)
        return profile_dir
    
    def create_chrome_options(self, headless: bool = False, download_dir: Optional[str] = None) -> Options:
        """Create Chrome options with all necessary settings"""
        options = Options()
        
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--disable-gpu')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Use isolated profile - CRITICAL for not interfering with user's Chrome
        profile_dir = self.get_isolated_profile_dir()
        options.add_argument(f"--user-data-dir={profile_dir}")
        print(f"[ChromeManager] Using isolated profile: {profile_dir}")
        
        if download_dir:
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
            }
            options.add_experimental_option("prefs", prefs)
        
        return options
    
    def initialize_driver(self, headless: bool = False, download_dir: Optional[str] = None) -> webdriver.Chrome:
        """
        Initialize Chrome WebDriver with robust fallback methods.
        
        Returns:
            webdriver.Chrome instance
            
        Raises:
            Exception if all methods fail
        """
        options = self.create_chrome_options(headless=headless, download_dir=download_dir)
        
        driver_initialized = False
        last_error = None
        driver = None
        
        # Detect Chrome version first
        self.chrome_version = self.get_installed_chrome_version()
        major_version = self.get_major_version(self.chrome_version) if self.chrome_version else None
        
        # Method 1: ChromeDriverManager with exact version match
        if self.chrome_version:
            try:
                print(f"[ChromeManager] Method 1: Exact version match for Chrome {self.chrome_version}...")
                downloaded_path = ChromeDriverManager(driver_version=self.chrome_version).install()
                
                # Fix path if wrong file returned
                if 'THIRD_PARTY_NOTICES' in downloaded_path or not os.path.isfile(downloaded_path):
                    driver_dir = os.path.dirname(downloaded_path)
                    found = self.find_chromedriver_in_dir(driver_dir)
                    if found:
                        downloaded_path = found
                
                self.fix_permissions(downloaded_path)
                self.driver_path = downloaded_path
                
                print(f"[ChromeManager] Using ChromeDriver: {downloaded_path}")
                service = Service(executable_path=downloaded_path)
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(40)
                driver_initialized = True
                print("[ChromeManager] ✅ Initialized successfully (Method 1: exact version)")
                
            except Exception as e:
                last_error = e
                print(f"[ChromeManager] Method 1 failed: {e}")
        
        # Method 2: ChromeDriverManager auto-detect
        if not driver_initialized:
            try:
                print("[ChromeManager] Method 2: ChromeDriverManager auto-detect...")
                downloaded_path = ChromeDriverManager().install()
                
                if 'THIRD_PARTY_NOTICES' in downloaded_path or not os.path.isfile(downloaded_path):
                    driver_dir = os.path.dirname(downloaded_path)
                    found = self.find_chromedriver_in_dir(driver_dir)
                    if found:
                        downloaded_path = found
                
                self.fix_permissions(downloaded_path)
                self.driver_path = downloaded_path
                
                print(f"[ChromeManager] Using ChromeDriver: {downloaded_path}")
                service = Service(executable_path=downloaded_path)
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(40)
                driver_initialized = True
                print("[ChromeManager] ✅ Initialized successfully (Method 2: auto-detect)")
                
            except Exception as e:
                last_error = e
                print(f"[ChromeManager] Method 2 failed: {e}")
        
        # Method 3: Let Selenium find chromedriver
        if not driver_initialized:
            try:
                print("[ChromeManager] Method 3: Selenium auto-find...")
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(40)
                driver_initialized = True
                print("[ChromeManager] ✅ Initialized successfully (Method 3: Selenium auto)")
                
            except Exception as e:
                last_error = e
                print(f"[ChromeManager] Method 3 failed: {e}")
        
        # Method 4: Search common paths
        if not driver_initialized:
            try:
                print("[ChromeManager] Method 4: Searching common paths...")
                common_paths = self.get_common_chromedriver_paths()
                
                for path in common_paths:
                    if os.path.exists(path):
                        self.fix_permissions(path)
                        try:
                            print(f"[ChromeManager] Trying: {path}")
                            service = Service(executable_path=path)
                            driver = webdriver.Chrome(service=service, options=options)
                            driver.set_page_load_timeout(40)
                            self.driver_path = path
                            driver_initialized = True
                            print("[ChromeManager] ✅ Initialized successfully (Method 4: common path)")
                            break
                        except Exception as path_error:
                            print(f"[ChromeManager] Path {path} failed: {path_error}")
                            continue
                            
            except Exception as e:
                last_error = e
                print(f"[ChromeManager] Method 4 failed: {e}")
        
        # Method 5: Clear cache and retry with exact version
        if not driver_initialized:
            try:
                print("[ChromeManager] Method 5: Clear cache and retry...")
                self.clear_driver_cache()
                
                # Re-detect Chrome version
                self.chrome_version = self.get_installed_chrome_version()
                
                if self.chrome_version:
                    downloaded_path = ChromeDriverManager(driver_version=self.chrome_version).install()
                else:
                    downloaded_path = ChromeDriverManager().install()
                
                if 'THIRD_PARTY_NOTICES' in downloaded_path or not os.path.isfile(downloaded_path):
                    driver_dir = os.path.dirname(downloaded_path)
                    found = self.find_chromedriver_in_dir(driver_dir)
                    if found:
                        downloaded_path = found
                
                self.fix_permissions(downloaded_path)
                self.driver_path = downloaded_path
                
                service = Service(executable_path=downloaded_path)
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(40)
                driver_initialized = True
                print("[ChromeManager] ✅ Initialized successfully (Method 5: cache cleared)")
                
            except Exception as e:
                last_error = e
                print(f"[ChromeManager] Method 5 failed: {e}")
        
        if not driver_initialized:
            error_msg = (
                f"All Chrome initialization methods failed.\n"
                f"Chrome version detected: {self.chrome_version or 'Unknown'}\n"
                f"Last error: {last_error}\n"
                f"Please ensure Google Chrome is installed."
            )
            print(f"[ChromeManager] ❌ {error_msg}")
            raise Exception(error_msg)
        
        return driver


# Convenience function for simple usage
def get_chrome_driver(headless: bool = False, download_dir: Optional[str] = None) -> webdriver.Chrome:
    """
    Get a configured Chrome WebDriver instance.
    
    Args:
        headless: Run in headless mode
        download_dir: Download directory path
        
    Returns:
        webdriver.Chrome instance
    """
    manager = ChromeManager()
    return manager.initialize_driver(headless=headless, download_dir=download_dir)
