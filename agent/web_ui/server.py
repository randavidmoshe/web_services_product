"""
Form Discoverer Agent - Web UI Server
Location: agent/web_ui/server.py

Flask server providing web-based UI for:
- Setup wizard (first-run configuration)
- Settings panel
- Live log viewer
- Test runner
"""

from flask import Flask, render_template, request, jsonify, Response
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv, set_key
import threading
import webbrowser

app = Flask(__name__)
app.config['SECRET_KEY'] = 'form-discoverer-secret-key-change-in-production'

# Global state
server_running = False
agent_connected = False


# ========== UTILITY FUNCTIONS ==========

def get_env_value(key, default=''):
    """Get value from .env file"""
    load_dotenv()
    return os.getenv(key, default)


def save_env_value(key, value):
    """Save value to .env file"""
    env_file = Path('.env')
    if not env_file.exists():
        env_file.touch()
    set_key(env_file, key, str(value))


def check_api_connection(api_url):
    """Check if API server is reachable"""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Try /health endpoint first, then root
        for endpoint in ['/health', '/']:
            try:
                response = requests.get(
                    f"{api_url}{endpoint}", 
                    timeout=5,
                    verify=False  # Allow self-signed certs in development
                )
                if response.status_code == 200:
                    return True
            except:
                continue
        return False
    except:
        return False


def create_folders():
    """Create required folders if they don't exist"""
    folders = [
        get_env_value('SCREENSHOT_FOLDER'),
        get_env_value('LOG_FOLDER'),
        get_env_value('FILES_FOLDER')
    ]
    for folder in folders:
        if folder:
            os.makedirs(folder, exist_ok=True)


# ========== MAIN ROUTES ==========

@app.route('/')
def index():
    """Root - redirect to appropriate page"""
    env_file = Path('.env')
    if env_file.exists():
        return render_template('dashboard.html')
    else:
        return render_template('setup.html')


@app.route('/setup')
def setup():
    """Setup wizard page"""
    return render_template('setup.html')


@app.route('/settings')
def settings():
    """Settings panel page"""
    import platform
    
    # IMPORTANT: Reload .env file to get latest saved values
    load_dotenv(override=True)
    
    # Get default Desktop path for current OS
    default_base = os.path.join(os.path.expanduser("~"), "Desktop", "automation_files")
    
    # Get folder values from .env, or use actual defaults
    screenshot_folder = get_env_value('SCREENSHOT_FOLDER')
    log_folder = get_env_value('LOG_FOLDER')
    files_folder = get_env_value('FILES_FOLDER')
    
    # If empty, show what agent_selenium actually uses as defaults
    if not screenshot_folder or screenshot_folder == "''":
        screenshot_folder = os.path.join(default_base, "screenshots")
    if not log_folder or log_folder == "''":
        log_folder = os.path.join(default_base, "logs")
    if not files_folder or files_folder == "''":
        files_folder = os.path.join(default_base, "files")
    
    config = {
        'api_url': get_env_value('API_URL', 'http://localhost:8001'),
        'agent_id': get_env_value('AGENT_ID'),
        'company_id': get_env_value('COMPANY_ID'),
        'user_id': get_env_value('USER_ID'),
        'browser': get_env_value('BROWSER', 'chrome'),
        'headless': get_env_value('DEFAULT_HEADLESS', 'false') == 'true',
        'screenshot_folder': screenshot_folder,
        'log_folder': log_folder,
        'files_folder': files_folder,
        'auto_start': get_env_value('AUTO_START', 'false') == 'true',
        'log_level': get_env_value('LOG_LEVEL', 'INFO'),
        'poll_interval': get_env_value('POLL_INTERVAL', '2'),
    }
    return render_template('settings.html', config=config)


@app.route('/logs')
def logs():
    """Log viewer page"""
    return render_template('logs.html')


@app.route('/tests')
def tests():
    """Test runner page"""
    return render_template('tests.html')


# ========== API ENDPOINTS ==========

@app.route('/api/setup/scan', methods=['POST'])
def api_scan():
    """Scan network for API server"""
    # Try common ports
    for port in [8001, 8000, 3000, 5000]:
        url = f"http://localhost:{port}"
        if check_api_connection(url):
            return jsonify({
                'success': True,
                'url': url
            })
    
    return jsonify({
        'success': False,
        'message': 'No API server found on common ports'
    })


@app.route('/api/setup/test-connection', methods=['POST'])
def api_test_connection():
    """Test connection to API server"""
    data = request.json
    url = data.get('url', '')
    
    if check_api_connection(url):
        return jsonify({'success': True})
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to connect to API server'
        })


@app.route('/api/setup/login', methods=['POST'])
def api_login():
    """Login and get agent credentials"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    api_url = data.get('api_url')
    
    try:
        import requests
        response = requests.post(
            f"{api_url}/api/auth/agent-login",
            json={'email': email, 'password': password},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'token': result.get('token'),
                'company_id': result.get('company_id'),
                'user_id': result.get('user_id')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        })


@app.route('/api/setup/save', methods=['POST'])
def api_save_setup():
    """Save setup configuration"""
    data = request.json
    
    try:
        # Save all configuration
        save_env_value('API_URL', data.get('api_url'))
        save_env_value('AGENT_TOKEN', data.get('token'))
        save_env_value('COMPANY_ID', data.get('company_id'))
        save_env_value('USER_ID', data.get('user_id'))
        save_env_value('AGENT_ID', data.get('agent_id'))
        save_env_value('BROWSER', data.get('browser', 'chrome'))
        save_env_value('DEFAULT_HEADLESS', str(data.get('headless', False)).lower())
        save_env_value('SCREENSHOT_FOLDER', data.get('screenshot_folder'))
        save_env_value('LOG_FOLDER', data.get('log_folder'))
        save_env_value('FILES_FOLDER', data.get('files_folder'))
        
        # Create folders
        create_folders()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to save configuration: {str(e)}'
        })


@app.route('/api/settings/save', methods=['POST'])
def api_save_settings():
    """Save settings changes"""
    data = request.json
    
    try:
        # Update configuration - save ALL fields
        save_env_value('API_URL', data.get('api_url'))
        save_env_value('BROWSER', data.get('browser'))
        save_env_value('DEFAULT_HEADLESS', str(data.get('headless')).lower())
        save_env_value('SCREENSHOT_FOLDER', data.get('screenshot_folder'))
        save_env_value('LOG_FOLDER', data.get('log_folder'))
        save_env_value('FILES_FOLDER', data.get('files_folder'))
        
        # Advanced settings
        if 'auto_start' in data:
            save_env_value('AUTO_START', str(data.get('auto_start')).lower())
        if 'log_level' in data:
            save_env_value('LOG_LEVEL', data.get('log_level'))
        if 'poll_interval' in data:
            save_env_value('POLL_INTERVAL', str(data.get('poll_interval')))
        
        # Create folders if changed
        create_folders()
        
        return jsonify({
            'success': True,
            'message': 'Settings saved! Restart agent for changes to take effect.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to save settings: {str(e)}'
        })


@app.route('/api/logs/stream')
def api_logs_stream():
    """Stream logs in real-time using Server-Sent Events"""
    def generate():
        log_file = Path(get_env_value('LOG_FOLDER', 'logs')) / 'agent.log'
        
        if not log_file.exists():
            yield f"data: Log file not found: {log_file}\n\n"
            return
        
        with open(log_file, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/logs/history')
def api_logs_history():
    """Get last N lines of automation results logs (customer-facing)"""
    lines = int(request.args.get('lines', 1000))
    
    # Get log folder from env, default to ~/Desktop/automation_files/logs
    default_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    base_folder = get_env_value('BASE_FOLDER', default_desktop)
    default_log_folder = os.path.join(base_folder, 'automation_files', 'logs')
    log_folder = Path(get_env_value('LOG_FOLDER', default_log_folder))
    
    # Find the most recent results_log file (automation logs, not system logs)
    try:
        log_files = sorted(log_folder.glob('results_log_*.log'), key=os.path.getmtime, reverse=True)
        if not log_files:
            return jsonify({'logs': ['No automation logs yet. Logs will appear when tests are executed.'], 'error': None})
        
        log_file = log_files[0]  # Get most recent
        
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
            return jsonify({'logs': recent_lines})
    except Exception as e:
        return jsonify({
            'error': f'Failed to read logs: {str(e)}',
            'logs': []
        })


@app.route('/api/tests/available')
def api_tests_available():
    """Get available tests from API server"""
    api_url = get_env_value('API_URL')
    
    try:
        import requests
        response = requests.get(
            f"{api_url}/api/tests/list",
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'tests': [],
                'error': 'Failed to fetch tests from API'
            })
    except Exception as e:
        return jsonify({
            'tests': [],
            'error': f'Failed to connect to API: {str(e)}'
        })


@app.route('/api/tests/run', methods=['POST'])
def api_tests_run():
    """Run selected tests"""
    data = request.json
    test_ids = data.get('test_ids', [])
    
    # TODO: Integrate with actual test execution
    # For now, just return success
    return jsonify({
        'success': True,
        'message': f'Started {len(test_ids)} tests'
    })


@app.route('/api/status')
def api_status():
    """Get agent status (for tray icon)"""
    global agent_connected
    
    api_url = get_env_value('API_URL')
    connected = check_api_connection(api_url) if api_url else False
    
    return jsonify({
        'connected': connected,
        'api_url': api_url,
        'agent_id': get_env_value('AGENT_ID')
    })


# ========== SERVER CONTROL ==========

def start_server(port=5555, open_browser=True):
    """Start Flask server in background thread"""
    global server_running
    
    if server_running:
        return
    
    server_running = True
    
    # Open browser after short delay
    if open_browser:
        def open_browser_delayed():
            time.sleep(1.5)
            webbrowser.open(f'http://localhost:{port}')
        
        threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    # Run Flask server
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def stop_server():
    """Stop Flask server"""
    global server_running
    server_running = False


if __name__ == '__main__':
    # Run directly for testing
    start_server(port=5555, open_browser=True)
