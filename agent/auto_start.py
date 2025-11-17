"""
Form Discoverer Agent - Auto-start Management
Location: agent/auto_start.py

Manages auto-start configuration for Windows, macOS, and Linux
"""

import os
import sys
import platform
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutoStartManager:
    """Manages auto-start configuration across platforms"""
    
    def __init__(self, app_name="FormDiscovererAgent"):
        self.app_name = app_name
        self.system = platform.system()
        self.executable_path = self._get_executable_path()
    
    def _get_executable_path(self):
        """Get path to current executable"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script
            return os.path.abspath(sys.argv[0])
    
    def enable_auto_start(self):
        """Enable auto-start for current platform"""
        try:
            if self.system == 'Windows':
                return self._enable_windows()
            elif self.system == 'Darwin':
                return self._enable_macos()
            elif self.system == 'Linux':
                return self._enable_linux()
            else:
                logger.error(f"Unsupported platform: {self.system}")
                return False
        except Exception as e:
            logger.error(f"Failed to enable auto-start: {e}")
            return False
    
    def disable_auto_start(self):
        """Disable auto-start for current platform"""
        try:
            if self.system == 'Windows':
                return self._disable_windows()
            elif self.system == 'Darwin':
                return self._disable_macos()
            elif self.system == 'Linux':
                return self._disable_linux()
            else:
                logger.error(f"Unsupported platform: {self.system}")
                return False
        except Exception as e:
            logger.error(f"Failed to disable auto-start: {e}")
            return False
    
    def is_auto_start_enabled(self):
        """Check if auto-start is enabled"""
        try:
            if self.system == 'Windows':
                return self._check_windows()
            elif self.system == 'Darwin':
                return self._check_macos()
            elif self.system == 'Linux':
                return self._check_linux()
            else:
                return False
        except Exception as e:
            logger.error(f"Failed to check auto-start status: {e}")
            return False
    
    # Windows implementation
    def _enable_windows(self):
        """Enable auto-start on Windows (Registry)"""
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Run',
            0,
            winreg.KEY_SET_VALUE
        )
        
        winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.executable_path)
        winreg.CloseKey(key)
        
        logger.info("Auto-start enabled (Windows Registry)")
        return True
    
    def _disable_windows(self):
        """Disable auto-start on Windows"""
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0,
                winreg.KEY_SET_VALUE
            )
            
            winreg.DeleteValue(key, self.app_name)
            winreg.CloseKey(key)
            
            logger.info("Auto-start disabled (Windows Registry)")
            return True
        except FileNotFoundError:
            # Already disabled
            return True
    
    def _check_windows(self):
        """Check if auto-start is enabled on Windows"""
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Run',
                0,
                winreg.KEY_READ
            )
            
            value, _ = winreg.QueryValueEx(key, self.app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
    
    # macOS implementation
    def _enable_macos(self):
        """Enable auto-start on macOS (LaunchAgent)"""
        plist_dir = Path.home() / 'Library' / 'LaunchAgents'
        plist_dir.mkdir(parents=True, exist_ok=True)
        
        plist_file = plist_dir / f'com.formdiscoverer.agent.plist'
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.formdiscoverer.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{self.executable_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
'''
        
        plist_file.write_text(plist_content)
        logger.info(f"Auto-start enabled (macOS LaunchAgent): {plist_file}")
        return True
    
    def _disable_macos(self):
        """Disable auto-start on macOS"""
        plist_file = Path.home() / 'Library' / 'LaunchAgents' / f'com.formdiscoverer.agent.plist'
        
        if plist_file.exists():
            plist_file.unlink()
            logger.info("Auto-start disabled (macOS LaunchAgent)")
        
        return True
    
    def _check_macos(self):
        """Check if auto-start is enabled on macOS"""
        plist_file = Path.home() / 'Library' / 'LaunchAgents' / f'com.formdiscoverer.agent.plist'
        return plist_file.exists()
    
    # Linux implementation
    def _enable_linux(self):
        """Enable auto-start on Linux (XDG autostart)"""
        autostart_dir = Path.home() / '.config' / 'autostart'
        autostart_dir.mkdir(parents=True, exist_ok=True)
        
        desktop_file = autostart_dir / f'formdiscoverer-agent.desktop'
        
        desktop_content = f'''[Desktop Entry]
Type=Application
Name=Form Discoverer Agent
Comment=AI-powered web testing agent
Exec={self.executable_path}
Icon=formdiscoverer
Terminal=false
Categories=Development;
X-GNOME-Autostart-enabled=true
'''
        
        desktop_file.write_text(desktop_content)
        logger.info(f"Auto-start enabled (Linux XDG autostart): {desktop_file}")
        return True
    
    def _disable_linux(self):
        """Disable auto-start on Linux"""
        desktop_file = Path.home() / '.config' / 'autostart' / f'formdiscoverer-agent.desktop'
        
        if desktop_file.exists():
            desktop_file.unlink()
            logger.info("Auto-start disabled (Linux XDG autostart)")
        
        return True
    
    def _check_linux(self):
        """Check if auto-start is enabled on Linux"""
        desktop_file = Path.home() / '.config' / 'autostart' / f'formdiscoverer-agent.desktop'
        return desktop_file.exists()
