"""
Form Discoverer Agent - Browser Traffic Capture
Location: agent/traffic_capture.py

Captures browser network traffic during testing using selenium-wire
"""

from seleniumwire import webdriver
from seleniumwire.utils import decode
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TrafficCapture:
    """
    Captures browser network traffic during QA testing.
    Used for debugging customer website issues.
    """
    
    def __init__(self, enabled=True, storage_path=None):
        self.enabled = enabled
        self.storage_path = Path(storage_path) if storage_path else None
        self.current_session_traffic = []
        
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Traffic storage path: {self.storage_path}")
    
    def get_driver_options(self, browser_type='chrome'):
        """Get selenium-wire options for driver"""
        if not self.enabled:
            return {}
        
        seleniumwire_options = {
            'disable_encoding': True,  # Capture response body
            'verify_ssl': False,  # Allow self-signed certs
        }
        
        logger.info("Traffic capture enabled for browser session")
        return {'seleniumwire_options': seleniumwire_options}
    
    def capture_traffic(self, driver):
        """Capture traffic from driver"""
        if not self.enabled:
            return []
        
        traffic_data = []
        
        try:
            for request in driver.requests:
                try:
                    # Extract request data
                    req_data = {
                        'timestamp': datetime.now().isoformat(),
                        'method': request.method,
                        'url': request.url,
                        'headers': dict(request.headers),
                        'body': request.body.decode('utf-8', errors='ignore') if request.body else None,
                    }
                    
                    # Extract response data if available
                    if request.response:
                        req_data['response'] = {
                            'status_code': request.response.status_code,
                            'reason': request.response.reason,
                            'headers': dict(request.response.headers),
                            'body': self._decode_response_body(request.response)
                        }
                    
                    traffic_data.append(req_data)
                    
                except Exception as e:
                    logger.error(f"Error capturing request: {e}")
            
            self.current_session_traffic.extend(traffic_data)
            logger.info(f"Captured {len(traffic_data)} requests")
            
        except Exception as e:
            logger.error(f"Error accessing driver requests: {e}")
        
        return traffic_data
    
    def _decode_response_body(self, response):
        """Decode response body"""
        try:
            body = decode(
                response.body,
                response.headers.get('Content-Encoding', 'identity')
            )
            return body.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.debug(f"Could not decode response body: {e}")
            return None
    
    def log_traffic(self, traffic_data, label=''):
        """Log traffic to console and file"""
        if not traffic_data:
            return
        
        logger.info(f"=== Traffic Capture {label} ===")
        for req in traffic_data:
            status = req.get('response', {}).get('status_code', 'N/A')
            logger.info(f"{req['method']} {req['url']} -> {status}")
        
        # Save to file if storage path set
        if self.storage_path:
            filename = f"traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.storage_path / filename
            
            try:
                with open(filepath, 'w') as f:
                    json.dump(traffic_data, f, indent=2)
                
                logger.info(f"Traffic saved to: {filepath}")
            except Exception as e:
                logger.error(f"Failed to save traffic: {e}")
    
    def get_session_traffic(self):
        """Get all traffic from current session"""
        return self.current_session_traffic
    
    def clear_session(self):
        """Clear current session traffic"""
        logger.info("Clearing traffic session")
        self.current_session_traffic = []
    
    def filter_traffic(self, url_pattern=None, method=None, status_code=None):
        """Filter captured traffic"""
        filtered = self.current_session_traffic
        
        if url_pattern:
            filtered = [t for t in filtered if url_pattern in t['url']]
        
        if method:
            filtered = [t for t in filtered if t['method'] == method]
        
        if status_code:
            filtered = [t for t in filtered 
                       if t.get('response', {}).get('status_code') == status_code]
        
        return filtered
    
    def print_traffic_for_debugging(self, url_pattern=None):
        """
        Print traffic for debugging (called by server when needed)
        This is triggered when server detects a bug and needs to see what happened
        """
        traffic = self.filter_traffic(url_pattern=url_pattern) if url_pattern else self.current_session_traffic
        
        logger.info("=" * 80)
        logger.info("DEBUG: Browser Traffic Capture (Customer Website)")
        logger.info("=" * 80)
        
        if not traffic:
            logger.info("No traffic captured")
            logger.info("=" * 80)
            return
        
        for i, req in enumerate(traffic, 1):
            logger.info(f"\n[{i}] {req['method']} {req['url']}")
            logger.info(f"    Time: {req['timestamp']}")
            
            # Request headers (abbreviated)
            if req.get('headers'):
                logger.info(f"    Request Headers: {list(req['headers'].keys())}")
            
            # Request body (if present)
            if req.get('body'):
                logger.info(f"    Request Body: {req['body'][:200]}...")
            
            # Response
            if req.get('response'):
                resp = req['response']
                logger.info(f"    Status: {resp['status_code']} {resp['reason']}")
                
                if resp.get('headers'):
                    logger.info(f"    Response Headers: {list(resp['headers'].keys())}")
                
                if resp.get('body'):
                    body_preview = resp['body'][:500] + '...' if len(resp['body']) > 500 else resp['body']
                    logger.info(f"    Response Body: {body_preview}")
        
        logger.info("=" * 80)
