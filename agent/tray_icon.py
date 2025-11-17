"""
Form Discoverer Agent - System Tray Icon
Location: agent/tray_icon.py

Manages system tray icon with status indicator and menu
"""

import pystray
from PIL import Image, ImageDraw
import threading
import webbrowser
import subprocess
import platform
import os
import logging

logger = logging.getLogger(__name__)


class AgentTrayIcon:
    def __init__(self, agent_config):
        self.agent_config = agent_config
        self.icon = None
        self.connected = False
        
    def create_icon_image(self, connected=False):
        """Create icon image with status indicator"""
        # Create 64x64 image
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw robot emoji-style icon
        # Body
        draw.rectangle([16, 24, 48, 56], fill='gray')
        # Head
        draw.rectangle([20, 8, 44, 32], fill='gray')
        # Eyes
        draw.rectangle([24, 14, 28, 18], fill='white')
        draw.rectangle([36, 14, 40, 18], fill='white')
        
        # Status indicator (bottom right corner)
        color = 'green' if connected else 'red'
        draw.ellipse([46, 46, 58, 58], fill=color)
        
        return img
    
    def update_status(self, connected):
        """Update connection status"""
        self.connected = connected
        if self.icon:
            self.icon.icon = self.create_icon_image(connected)
            status = 'Connected' if connected else 'Disconnected'
            self.icon.title = f"Form Discoverer Agent - {status}"
    
    def open_settings(self):
        """Open settings in browser"""
        webbrowser.open('http://localhost:5555/settings')
    
    def open_logs(self):
        """Open logs in browser"""
        webbrowser.open('http://localhost:5555/logs')
    
    def open_tests(self):
        """Open test runner in browser"""
        webbrowser.open('http://localhost:5555/tests')
    
    def open_folder(self, folder_path):
        """Open folder in file explorer"""
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(folder_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            logger.error(f"Error opening folder: {e}")
    
    def open_screenshots_folder(self):
        """Open screenshots folder"""
        folder = self.agent_config.screenshot_folder
        if folder and os.path.exists(folder):
            self.open_folder(folder)
        else:
            logger.warning(f"Screenshots folder not found: {folder}")
    
    def open_logs_folder(self):
        """Open logs folder"""
        folder = self.agent_config.log_folder
        if folder and os.path.exists(folder):
            self.open_folder(folder)
        else:
            logger.warning(f"Logs folder not found: {folder}")
    
    def restart_agent(self):
        """Restart agent"""
        logger.info("Restarting agent...")
        # In production: send signal to main process to restart
        import sys
        import os
        python = sys.executable
        os.execl(python, python, *sys.argv)
    
    def quit_agent(self):
        """Quit agent"""
        logger.info("Quitting agent...")
        self.icon.stop()
        import sys
        sys.exit(0)
    
    def create_menu(self):
        """Create tray menu"""
        status_emoji = '🟢' if self.connected else '🔴'
        status_text = 'Connected' if self.connected else 'Disconnected'
        
        return pystray.Menu(
            pystray.MenuItem(
                f"{status_emoji} Status: {status_text}",
                None,  # Not clickable
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('⚙️ Settings', self.open_settings),
            pystray.MenuItem('📊 View Logs', self.open_logs),
            pystray.MenuItem('📁 Open Screenshots', self.open_screenshots_folder),
            pystray.MenuItem('📁 Open Logs Folder', self.open_logs_folder),
            pystray.MenuItem('🧪 Run Tests', self.open_tests),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('🔄 Restart Agent', self.restart_agent),
            pystray.MenuItem('❌ Quit', self.quit_agent)
        )
    
    def start(self):
        """Start tray icon in background thread"""
        logger.info("Starting system tray icon...")
        self.icon = pystray.Icon(
            'FormDiscovererAgent',
            self.create_icon_image(self.connected),
            'Form Discoverer Agent',
            self.create_menu()
        )
        
        # Run in separate thread
        threading.Thread(target=self.icon.run, daemon=True).start()
        logger.info("System tray icon started")
    
    def stop(self):
        """Stop tray icon"""
        if self.icon:
            logger.info("Stopping system tray icon...")
            self.icon.stop()
