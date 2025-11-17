# agent_config.py
# Agent Configuration Management

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


class AgentConfig:
    """
    Agent configuration loaded from .env file
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Load configuration from .env file
        
        Args:
            config_file: Path to .env file (default: .env in current directory)
        """
        # Load .env file
        if config_file:
            env_path = Path(config_file)
        else:
            env_path = Path(__file__).parent / '.env'
        
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"✅ Loaded configuration from: {env_path}")
        else:
            print(f"⚠️  No .env file found at: {env_path}")
            print(f"   Using environment variables or defaults")
        
        # Server connection settings
        self.api_url = os.getenv('API_URL', 'http://localhost:8000')
        self.agent_token = os.getenv('AGENT_TOKEN', '')
        
        # Agent identification (pre-configured by server when agent is downloaded)
        self.agent_id = os.getenv('AGENT_ID', self._generate_agent_id())
        self.company_id = int(os.getenv('COMPANY_ID', '0'))
        self.user_id = int(os.getenv('USER_ID', '0'))
        
        # Agent behavior settings
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '30'))  # seconds
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL', '30'))  # seconds
        
        # Folder paths - expand ~ for cross-platform support
        screenshot_folder_raw = os.getenv('SCREENSHOT_FOLDER', '')
        self.screenshot_folder = os.path.expanduser(screenshot_folder_raw) if screenshot_folder_raw else ''  # Empty = use Desktop

        log_folder_raw = os.getenv('LOG_FOLDER', os.path.join(os.path.expanduser('~'), 'FormDiscovererAgent', 'logs'))
        self.log_folder = os.path.expanduser(log_folder_raw)
        
        files_folder_raw = os.getenv('FILES_FOLDER', os.path.join(os.path.expanduser('~'), 'FormDiscovererAgent', 'files'))
        self.files_folder = os.path.expanduser(files_folder_raw)
        
        self.capture_traffic = os.getenv('CAPTURE_TRAFFIC', 'false').lower() == 'true'

        # Browser settings
        self.default_browser = os.getenv('DEFAULT_BROWSER', 'chrome')
        self.default_headless = os.getenv('DEFAULT_HEADLESS', 'false').lower() == 'true'
        
        # Validate required settings
        #if not self.agent_token:
        #    raise ValueError("AGENT_TOKEN is required in .env file")
        
        #if self.company_id == 0:
        #    raise ValueError("COMPANY_ID is required in .env file")
        
        #if self.user_id == 0:
        #    raise ValueError("USER_ID is required in .env file")
    
    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID if not provided"""
        import uuid
        return f"agent-{uuid.uuid4().hex[:12]}"
    
    def to_dict(self) -> dict:
        """Return configuration as dictionary"""
        return {
            'api_url': self.api_url,
            'agent_id': self.agent_id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'poll_interval': self.poll_interval,
            'heartbeat_interval': self.heartbeat_interval,
            'screenshot_folder': self.screenshot_folder,
            'default_browser': self.default_browser,
            'default_headless': self.default_headless
        }
    
    def __repr__(self):
        """String representation (hide token)"""
        return (
            f"AgentConfig(\n"
            f"  api_url={self.api_url}\n"
            f"  agent_id={self.agent_id}\n"
            f"  company_id={self.company_id}\n"
            f"  user_id={self.user_id}\n"
            f"  token={'*' * 10 if self.agent_token else 'NOT SET'}\n"
            f")"
        )
