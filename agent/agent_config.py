# agent_config.py
# Agent Configuration Management
# UPDATED: Added API Key support for Part 2 authentication

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
        # NOTE: Changed to HTTPS for secure communication
        self.api_url = os.getenv('API_URL', 'https://localhost')
        self.agent_token = os.getenv('AGENT_TOKEN', '')
        
        # API Key for authentication (received during registration)
        self.api_key = os.getenv('API_KEY', '')
        
        # SSL verification (set to False for self-signed certs in development)
        self.ssl_verify = os.getenv('SSL_VERIFY', 'false').lower() == 'true'
        
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
        
        # Store path to .env for saving API key later
        self._env_path = env_path
    
    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID if not provided"""
        import uuid
        return f"agent-{uuid.uuid4().hex[:12]}"
    
    def save_api_key(self, api_key: str):
        """
        Save API key to .env file after registration.
        This is called when the agent receives an API key from the server.
        """
        env_path = self._env_path
        
        if env_path.exists():
            # Read existing content
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Check if API_KEY line exists
            key_found = False
            for i, line in enumerate(lines):
                if line.startswith('API_KEY='):
                    lines[i] = f"API_KEY='{api_key}'\n"
                    key_found = True
                    break
            
            # Add API_KEY if not found
            if not key_found:
                lines.append(f"\n# API Key (auto-saved after registration)\nAPI_KEY='{api_key}'\n")
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)
        else:
            # Create new .env file with API key
            with open(env_path, 'w') as f:
                f.write(f"API_KEY='{api_key}'\n")
        
        # Update current config
        self.api_key = api_key
        print(f"✅ API key saved to {env_path}")
    
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
            'default_headless': self.default_headless,
            'ssl_verify': self.ssl_verify,
            'has_api_key': bool(self.api_key)
        }
    
    def __repr__(self):
        """String representation (hide sensitive data)"""
        return (
            f"AgentConfig(\n"
            f"  api_url={self.api_url}\n"
            f"  agent_id={self.agent_id}\n"
            f"  company_id={self.company_id}\n"
            f"  user_id={self.user_id}\n"
            f"  ssl_verify={self.ssl_verify}\n"
            f"  api_key={'*' * 10 if self.api_key else 'NOT SET'}\n"
            f"  token={'*' * 10 if self.agent_token else 'NOT SET'}\n"
            f")"
        )
