"""
Activity Logger - Unified Logging System for Quattera Agent
Location: agent/activity_logger.py

Replaces results_logger with a unified system that:
1. Streams to local Web UI via memory queue (real-time)
2. Writes to activity-specific log files (local persistence)
3. Batches logs to server on activity completion (scalable)

Usage:
    from activity_logger import ActivityLogger
    from agent_config import AgentConfig
    
    config = AgentConfig()
    logger = ActivityLogger(config)
    
    # Start a session
    logger.start_session(
        activity_type='discovery',
        session_id=123,
        project_id=5,
        company_id=10,
        user_id=42
    )
    
    # Log milestones
    logger.log("🔍 Discovery started")
    logger.log("✅ Found form: Employee Form", metadata={"form_name": "Employee Form"})
    logger.warning("⚠️ Popup dismissed")
    logger.error("❌ Login failed")
    
    # Complete session (triggers server upload)
    logger.complete()
"""

import os
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from collections import deque
from pathlib import Path
import json
import requests

import zipfile
import glob
import io


# ============================================================================
# Log Entry Data Class
# ============================================================================

class LogEntry:
    """Represents a single log entry."""
    
    def __init__(
        self,
        message: str,
        level: str = 'info',
        category: str = 'milestone',
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        session_id: Optional[int] = None,
        activity_type: Optional[str] = None
    ):
        self.timestamp = timestamp or datetime.utcnow()
        self.level = level
        self.category = category
        self.message = message
        self.metadata = metadata or {}
        self.session_id = session_id
        self.activity_type = activity_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'level': self.level,
            'category': self.category,
            'message': self.message,
            'metadata': self.metadata
        }
    
    def to_sse_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for SSE streaming."""
        return {
            'timestamp': self.timestamp.isoformat() + 'Z',
            'level': self.level,
            'message': self.message,
            'activity_type': self.activity_type,
            'session_id': self.session_id
        }
    
    def to_file_line(self) -> str:
        """Convert to log file line format."""
        ts = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        session = f"[{self.session_id}]" if self.session_id else "[-]"
        return f"[{ts}] {session} [{self.level.upper()}] {self.message}"


# ============================================================================
# Subscriber Base Class
# ============================================================================

class LogSubscriber:
    """Base class for log subscribers."""
    
    def on_log(self, entry: LogEntry):
        """Called when a log entry is emitted."""
        raise NotImplementedError
    
    def on_session_start(self, activity_type: str, session_id: int, metadata: Dict):
        """Called when a new session starts."""
        pass
    
    def on_session_complete(self, summary: Optional[str] = None):
        """Called when session completes."""
        pass
    
    def on_session_fail(self, error_message: str, error_code: Optional[str] = None):
        """Called when session fails."""
        pass


# ============================================================================
# Memory Queue Writer (for Web UI SSE)
# ============================================================================

class MemoryQueueWriter(LogSubscriber):
    """
    Writes log entries to an in-memory queue for real-time streaming.
    The Web UI SSE endpoint reads from this queue.
    """
    
    def __init__(self, max_size: int = 1000):
        self.queue = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self._read_position = 0
    
    def on_log(self, entry: LogEntry):
        """Add entry to queue."""
        with self.lock:
            self.queue.append(entry)
    
    def get_new_entries(self) -> List[LogEntry]:
        """Get entries added since last read (for SSE polling)."""
        with self.lock:
            entries = list(self.queue)
            # Return all entries (SSE client tracks its own position)
            return entries
    
    def get_entries_since(self, last_timestamp: Optional[datetime] = None) -> List[LogEntry]:
        """Get entries since a specific timestamp."""
        with self.lock:
            if last_timestamp is None:
                return list(self.queue)
            return [e for e in self.queue if e.timestamp > last_timestamp]
    
    def clear(self):
        """Clear the queue."""
        with self.lock:
            self.queue.clear()


# ============================================================================
# Local File Writer
# ============================================================================

class LocalFileWriter(LogSubscriber):
    """
    Writes log entries to activity-specific local files.
    Uses config.log_folder for path (user configurable).
    """
    
    def __init__(self, log_folder: str, retention_days: int = 7):
        self.log_folder = Path(log_folder)
        self.retention_days = retention_days
        self.current_file = None
        self.current_date = None
        self.activity_type = None
        self.lock = threading.Lock()
        self._file_handle = None
        
        # Ensure folder exists
        self.log_folder.mkdir(parents=True, exist_ok=True)
        
        # Clean old files on init
        self._cleanup_old_files()
    
    def on_session_start(self, activity_type: str, session_id: int, metadata: Dict):
        """Open/prepare log file for this activity type."""
        self.activity_type = activity_type
        self._ensure_file_open()
    
    def on_log(self, entry: LogEntry):
        """Write entry to file."""
        with self.lock:
            self._ensure_file_open()
            if self._file_handle:
                try:
                    line = entry.to_file_line()
                    self._file_handle.write(line + '\n')
                    self._file_handle.flush()
                except Exception as e:
                    # Don't crash on write errors
                    pass
    
    def on_session_complete(self, summary: Optional[str] = None):
        """Flush and optionally close file."""
        with self.lock:
            if self._file_handle:
                try:
                    self._file_handle.flush()
                except:
                    pass
    
    def _ensure_file_open(self):
        """Ensure we have an open file handle for today's log."""
        today = datetime.utcnow().strftime('%Y%m%d')
        activity = self.activity_type or 'general'
        
        # Check if we need a new file (new day or new activity type)
        if self.current_date != today or self.current_file is None:
            # Close old file
            if self._file_handle:
                try:
                    self._file_handle.close()
                except:
                    pass
            
            # Open new file
            self.current_date = today
            filename = f"{activity}_{today}.log"
            self.current_file = self.log_folder / filename
            
            try:
                self._file_handle = open(self.current_file, 'a', encoding='utf-8')
            except Exception as e:
                self._file_handle = None
    
    def _cleanup_old_files(self):
        """Delete log files older than retention_days."""
        try:
            cutoff = datetime.utcnow().timestamp() - (self.retention_days * 24 * 60 * 60)
            for log_file in self.log_folder.glob('*.log'):
                try:
                    if log_file.stat().st_mtime < cutoff:
                        log_file.unlink()
                except:
                    pass
        except:
            pass
    
    def close(self):
        """Close file handle."""
        with self.lock:
            if self._file_handle:
                try:
                    self._file_handle.close()
                except:
                    pass
                self._file_handle = None


# ============================================================================
# Server Batcher
# ============================================================================

class ServerBatcher(LogSubscriber):
    """
    Collects log entries during activity execution and sends them
    to the server in a single batch on completion.
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: str = '',
        jwt_token: str = '',
        ssl_verify: bool = False,
        max_retries: int = 3
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.ssl_verify = ssl_verify
        self.max_retries = max_retries
        
        # Session state
        self.entries: List[LogEntry] = []
        self.activity_type: Optional[str] = None
        self.session_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.company_id: Optional[int] = None
        self.user_id: Optional[int] = None
        self.lock = threading.Lock()
        self.upload_urls: Dict[str, str] = {}
        self.screenshots_folder: Optional[str] = None
        self.form_files_folder: Optional[str] = None
    
    def update_auth(self, api_key: str = '', jwt_token: str = ''):
        """Update authentication credentials (for JWT refresh)."""
        self.api_key = api_key
        self.jwt_token = jwt_token
    
    def on_session_start(self, activity_type: str, session_id: int, metadata: Dict):
        """Initialize for new session."""
        with self.lock:
            self.entries = []
            self.activity_type = activity_type
            self.session_id = session_id
            self.project_id = metadata.get('project_id')
            self.company_id = metadata.get('company_id')
            self.user_id = metadata.get('user_id')
            self.upload_urls = metadata.get('upload_urls', {})
            self.screenshots_folder = metadata.get('screenshots_folder')
            self.form_files_folder = metadata.get('form_files_folder')
    
    def on_log(self, entry: LogEntry):
        """Collect entry for batch upload."""
        with self.lock:
            self.entries.append(entry)
    
    def on_session_complete(self, summary: Optional[str] = None):
        """Send batch to server."""
        self._send_batch()
        if self.activity_type in ('mapping', 'test_run') and self.screenshots_folder:
            self._send_screenshots_to_s3()
        if self.activity_type == 'mapping' and self.form_files_folder:
            self._send_form_files_to_s3()
    
    def on_session_fail(self, error_message: str, error_code: Optional[str] = None):
        """Send batch to server (even on failure)."""
        self._send_batch()
        if self.activity_type in ('mapping', 'test_run') and self.screenshots_folder:
            self._send_screenshots_to_s3()


    def _send_batch(self):
        """Upload ALL logs to S3, then confirm with API."""
        print(f"[ActivityLogger] _send_batch called")

        with self.lock:
            if not self.entries:
                print(f"[ActivityLogger] No entries to send")
                return
            entries_to_send = self.entries.copy()
            self.entries = []

        upload_url = self.upload_urls.get('logs')
        s3_key = self.upload_urls.get('logs_s3_key')

        if not upload_url or not s3_key:
            print(f"[ActivityLogger] No upload URL for logs - skipping S3 upload")
            return

        # Convert entries to JSON
        entries_dicts = [e.to_dict() for e in entries_to_send]
        entries_json = json.dumps(entries_dicts)

        print(f"[ActivityLogger] Uploading {len(entries_dicts)} log entries ({len(entries_json)} bytes) to S3")

        try:
            # Upload to S3
            response = requests.put(
                upload_url,
                data=entries_json.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                timeout=120
            )

            if response.status_code not in (200, 201):
                print(f"[ActivityLogger] S3 upload failed: {response.status_code} - {response.text[:200]}")
                return

            print(f"[ActivityLogger] S3 upload SUCCESS, confirming with API")

            # Confirm with API
            confirm_payload = {
                'activity_type': self.activity_type,
                'session_id': self.session_id,
                'project_id': self.project_id,
                'company_id': self.company_id,
                'user_id': self.user_id,
                's3_key': s3_key
            }

            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['X-Agent-API-Key'] = self.api_key
            if self.jwt_token:
                headers['Authorization'] = f'Bearer {self.jwt_token}'

            confirm_url = f"{self.api_url}/api/activity-logs/logs/confirm"
            confirm_response = requests.post(
                confirm_url,
                json=confirm_payload,
                headers=headers,
                timeout=30,
                verify=self.ssl_verify
            )

            if confirm_response.status_code in (200, 201):
                print(f"[ActivityLogger] Log confirm SUCCESS")
            else:
                print(f"[ActivityLogger] Log confirm failed: {confirm_response.status_code}")

        except Exception as e:
            print(f"[ActivityLogger] Log upload error: {e}")

    def _send_screenshots_to_s3(self):
        """Zip and upload screenshots to S3. Lambda will unzip automatically."""
        upload_url = self.upload_urls.get('screenshots_zip')

        if not upload_url:
            print(f"[ActivityLogger] No screenshot upload URL")
            return

        if not self.screenshots_folder or not os.path.exists(self.screenshots_folder):
            print(f"[ActivityLogger] Screenshots folder not found: {self.screenshots_folder}")
            return

        # Find screenshot files for this session
        screenshot_files = self._find_session_screenshots()

        if not screenshot_files:
            print(f"[ActivityLogger] No screenshot files found for session {self.session_id}")
            return

        print(f"[ActivityLogger] Found {len(screenshot_files)} screenshots to upload")

        # Create zip file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filepath in screenshot_files:
                filename = os.path.basename(filepath)
                zip_file.write(filepath, filename)

        zip_buffer.seek(0)
        zip_data = zip_buffer.read()

        print(f"[ActivityLogger] Created zip: {len(zip_data)} bytes")

        try:
            # Upload zip to S3 - Lambda will process automatically
            print(f"[ActivityLogger] Uploading screenshots zip to S3")
            response = requests.put(
                upload_url,
                data=zip_data,
                headers={'Content-Type': 'application/zip'},
                timeout=300  # 5 min for large uploads
            )

            if response.status_code in (200, 201):
                # Check which processor to use (lambda or celery)
                screenshot_processor = os.environ.get('SCREENSHOT_PROCESSOR', 'celery').lower()

                if screenshot_processor == 'lambda':
                    # Lambda: S3 trigger will process automatically
                    print(f"[ActivityLogger] Screenshot upload SUCCESS - Lambda will process")
                else:
                    # Celery: call confirm endpoint to trigger processing
                    print(f"[ActivityLogger] Screenshot upload SUCCESS, confirming with API")

                    s3_key = self.upload_urls.get('screenshots_zip_s3_key')
                    confirm_payload = {
                        'activity_type': self.activity_type,
                        'session_id': self.session_id,
                        'project_id': self.project_id,
                        'company_id': self.company_id,
                        's3_key': s3_key
                    }

                    headers = {'Content-Type': 'application/json'}
                    if self.api_key:
                        headers['X-Agent-API-Key'] = self.api_key
                    if self.jwt_token:
                        headers['Authorization'] = f'Bearer {self.jwt_token}'

                    confirm_url = f"{self.api_url}/api/activity-logs/screenshots/confirm-zip"
                    try:
                        confirm_response = requests.post(
                            confirm_url,
                            json=confirm_payload,
                            headers=headers,
                            timeout=30,
                            verify=self.ssl_verify
                        )

                        if confirm_response.status_code in (200, 201):
                            print(f"[ActivityLogger] Screenshot confirm SUCCESS")
                        else:
                            print(f"[ActivityLogger] Screenshot confirm failed: {confirm_response.status_code}")
                    except Exception as confirm_error:
                        print(f"[ActivityLogger] Screenshot confirm error: {confirm_error}")
            else:
                print(f"[ActivityLogger] Screenshot upload failed: {response.status_code}")

        except Exception as e:
            print(f"[ActivityLogger] Screenshot upload error: {e}")

    def _find_session_screenshots(self) -> List[str]:
        """Find screenshot files for the current session."""
        screenshot_files = []

        # Option 1: Session-specific subfolder
        session_folder = os.path.join(self.screenshots_folder, str(self.session_id))
        if os.path.exists(session_folder):
            screenshot_files = glob.glob(os.path.join(session_folder, '*.png'))

        # Option 2: Files matching session_id in filename
        if not screenshot_files:
            screenshot_files = glob.glob(os.path.join(self.screenshots_folder, f'*_{self.session_id}_*.png'))

        # Option 3: Check mapping subfolder
        if not screenshot_files:
            mapping_folder = os.path.join(self.screenshots_folder, 'mapping')
            if os.path.exists(mapping_folder):
                screenshot_files = glob.glob(os.path.join(mapping_folder, f'*_{self.session_id}_*.png'))

        return screenshot_files

    def _send_form_files_to_s3(self):
        """Zip and upload form files to S3 for test runner to use later."""
        upload_url = self.upload_urls.get('form_files_zip')

        if not upload_url:
            print(f"[ActivityLogger] No form files upload URL")
            return

        if not self.form_files_folder or not os.path.exists(self.form_files_folder):
            print(f"[ActivityLogger] Form files folder not found: {self.form_files_folder}")
            return

        # Find form files for this session
        session_folder = os.path.join(self.form_files_folder, str(self.session_id))
        if not os.path.exists(session_folder):
            print(f"[ActivityLogger] No form files folder for session {self.session_id}")
            return

        # Get all files in session folder
        form_files = []
        for f in os.listdir(session_folder):
            filepath = os.path.join(session_folder, f)
            if os.path.isfile(filepath):
                form_files.append(filepath)

        if not form_files:
            print(f"[ActivityLogger] No form files found for session {self.session_id}")
            return

        print(f"[ActivityLogger] Found {len(form_files)} form files to upload")

        # Create zip file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filepath in form_files:
                filename = os.path.basename(filepath)
                zip_file.write(filepath, filename)

        zip_buffer.seek(0)
        zip_data = zip_buffer.read()

        print(f"[ActivityLogger] Created form files zip: {len(zip_data)} bytes")

        try:
            # Upload zip to S3
            print(f"[ActivityLogger] Uploading form files zip to S3")
            response = requests.put(
                upload_url,
                data=zip_data,
                headers={'Content-Type': 'application/zip'},
                timeout=300
            )

            if response.status_code in (200, 201):
                # Check which processor to use
                form_files_processor = os.environ.get('SCREENSHOT_PROCESSOR', 'celery').lower()

                if form_files_processor == 'lambda':
                    print(f"[ActivityLogger] Form files upload SUCCESS - Lambda will process")
                else:
                    # Celery: call confirm endpoint
                    print(f"[ActivityLogger] Form files upload SUCCESS, confirming with API")

                    s3_key = self.upload_urls.get('form_files_zip_s3_key')
                    confirm_payload = {
                        'activity_type': self.activity_type,
                        'session_id': self.session_id,
                        'project_id': self.project_id,
                        'company_id': self.company_id,
                        'form_page_route_id': self.upload_urls.get('form_page_route_id'),
                        's3_key': s3_key
                    }

                    headers = {'Content-Type': 'application/json'}
                    if self.api_key:
                        headers['X-Agent-API-Key'] = self.api_key
                    if self.jwt_token:
                        headers['Authorization'] = f'Bearer {self.jwt_token}'

                    confirm_url = f"{self.api_url}/api/activity-logs/form-files/confirm-zip"
                    try:
                        confirm_response = requests.post(
                            confirm_url,
                            json=confirm_payload,
                            headers=headers,
                            timeout=30,
                            verify=self.ssl_verify
                        )

                        if confirm_response.status_code in (200, 201):
                            print(f"[ActivityLogger] Form files confirm SUCCESS")
                        else:
                            print(f"[ActivityLogger] Form files confirm failed: {confirm_response.status_code}")
                    except Exception as confirm_error:
                        print(f"[ActivityLogger] Form files confirm error: {confirm_error}")
            else:
                print(f"[ActivityLogger] Form files upload failed: {response.status_code}")

        except Exception as e:
            print(f"[ActivityLogger] Form files upload error: {e}")

# ============================================================================
# Activity Logger (Main Class)
# ============================================================================

class ActivityLogger:
    """
    Unified logging system for the Quattera Agent.
    Replaces results_logger with a subscriber-based architecture.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config=None):
        """Singleton pattern - one logger per agent."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config=None):
        """
        Initialize the activity logger.
        
        Args:
            config: AgentConfig instance with log_folder, api_url, etc.
        """
        # Only initialize once (singleton)
        if self._initialized:
            return
        
        self.config = config
        self.subscribers: List[LogSubscriber] = []
        
        # Session state
        self.activity_type: Optional[str] = None
        self.session_id: Optional[int] = None
        self.project_id: Optional[int] = None
        self.company_id: Optional[int] = None
        self.user_id: Optional[int] = None
        self.network_id: Optional[int] = None
        self.session_active = False
        
        # Initialize subscribers
        self._init_subscribers()
        
        self._initialized = True
    
    def _init_subscribers(self):
        """Initialize the three subscribers."""
        # 1. Memory Queue (for Web UI SSE)
        self.memory_queue = MemoryQueueWriter(max_size=1000)
        self.subscribers.append(self.memory_queue)
        
        # 2. Local File Writer (uses config.log_folder)
        log_folder = getattr(self.config, 'log_folder', None)
        if not log_folder:
            # Default fallback
            log_folder = os.path.join(
                os.path.expanduser('~'),
                'Desktop',
                'automation_files',
                'logs'
            )
        self.file_writer = LocalFileWriter(log_folder=log_folder)
        self.subscribers.append(self.file_writer)
        
        # 3. Server Batcher (batch upload on complete)
        api_url = getattr(self.config, 'api_url', '')
        api_key = getattr(self.config, 'api_key', '')
        ssl_verify = getattr(self.config, 'ssl_verify', False)
        
        self.server_batcher = ServerBatcher(
            api_url=api_url,
            api_key=api_key,
            ssl_verify=ssl_verify
        )
        self.subscribers.append(self.server_batcher)
    
    def update_auth(self, api_key: str = '', jwt_token: str = ''):
        """Update authentication for server batcher (for JWT refresh)."""
        self.server_batcher.update_auth(api_key=api_key, jwt_token=jwt_token)
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def start_session(
        self,
        activity_type: str,
        session_id: int,
        project_id: int,
        company_id: int,
        user_id: int,
        network_id: Optional[int] = None,
        upload_urls: Optional[Dict[str, str]] = None,
        screenshots_folder: Optional[str] = None,
        form_files_folder: Optional[str] = None
    ):
        """
        Start a new logging session.
        
        Args:
            activity_type: 'discovery', 'mapping', or 'test_run'
            session_id: The session ID (crawl_session_id, mapper_session_id, etc.)
            project_id: Project ID
            company_id: Company ID  
            user_id: User ID
            network_id: Optional network ID
        """
        self.activity_type = activity_type
        self.session_id = session_id
        self.project_id = project_id
        self.company_id = company_id
        self.user_id = user_id
        self.network_id = network_id
        self.session_active = True
        
        metadata = {
            'project_id': project_id,
            'company_id': company_id,
            'user_id': user_id,
            'network_id': network_id,
            'upload_urls': upload_urls or {},
            'screenshots_folder': screenshots_folder,
            'form_files_folder': form_files_folder
        }
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber.on_session_start(activity_type, session_id, metadata)
            except Exception:
                pass
    
    def complete(self, summary: Optional[str] = None):
        """
        Complete the current session.
        Triggers ServerBatcher to upload logs to server.
        """
        if not self.session_active:
            return
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber.on_session_complete(summary)
            except Exception:
                pass
        
        self.session_active = False
    
    def fail(self, error_message: str, error_code: Optional[str] = None):
        """
        Fail the current session with an error.
        Logs the error then completes the session.
        """
        self.error(f"❌ {error_message}")
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber.on_session_fail(error_message, error_code)
            except Exception:
                pass
        
        self.session_active = False
    
    # ========================================================================
    # Logging Methods
    # ========================================================================
    
    def log(
        self,
        message: str,
        level: str = 'info',
        category: str = 'milestone',
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a message.
        
        Args:
            message: The log message
            level: 'info', 'warning', or 'error'
            category: 'milestone' or 'debug'
            metadata: Optional structured data
        """
        entry = LogEntry(
            message=message,
            level=level,
            category=category,
            metadata=metadata,
            session_id=self.session_id,
            activity_type=self.activity_type
        )
        
        # Emit to all subscribers
        for subscriber in self.subscribers:
            try:
                subscriber.on_log(entry)
            except Exception:
                pass
    
    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log an info message (backward compatible with results_logger)."""
        self.log(message, level='info', metadata=metadata)
    
    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log a warning message (backward compatible with results_logger)."""
        self.log(message, level='warning', metadata=metadata)
    
    def error(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log an error message (backward compatible with results_logger)."""
        self.log(message, level='error', metadata=metadata)
    
    # ========================================================================
    # Web UI Support
    # ========================================================================
    
    def get_queue(self) -> MemoryQueueWriter:
        """Get the memory queue for Web UI SSE endpoint."""
        return self.memory_queue
    
    def get_recent_entries(self, count: int = 100) -> List[Dict]:
        """Get recent log entries for Web UI."""
        entries = list(self.memory_queue.queue)[-count:]
        return [e.to_sse_dict() for e in entries]


# ============================================================================
# Global Instance Helper
# ============================================================================

_global_logger: Optional[ActivityLogger] = None


def get_activity_logger() -> Optional[ActivityLogger]:
    """Get the global ActivityLogger instance."""
    return _global_logger


def init_activity_logger(config) -> ActivityLogger:
    """Initialize and return the global ActivityLogger instance."""
    global _global_logger
    _global_logger = ActivityLogger(config)
    return _global_logger
