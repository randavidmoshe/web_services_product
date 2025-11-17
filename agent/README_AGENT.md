# Form Discoverer Agent

AI-powered web testing agent that runs on your desktop.

## Features

- 🤖 **System Tray Integration** - Runs quietly in background
- 🌐 **Web-Based UI** - Modern setup wizard and control panel
- 📊 **Live Log Viewer** - See what's happening in real-time
- 🧪 **Test Runner** - Execute tests from your projects
- 🔍 **Traffic Capture** - Debug customer website issues
- ⚙️ **Auto-Start** - Launch automatically on system boot
- 🔒 **Secure** - All data stays on your network

## Quick Start

### 1. Download & Install

Get the installer for your platform:
- Windows: `FormDiscovererAgent-Setup-Windows.exe`
- macOS: `FormDiscovererAgent-2.0.0-macOS.dmg`
- Linux: `FormDiscovererAgent-2.0.0-Linux.tar.gz`

### 2. First Run

The agent will open a setup wizard in your browser:

1. **API Server**: Enter your API server URL
2. **Login**: Authenticate with your credentials
3. **Configure**: Choose browser and folders
4. **Done**: Agent starts working!

### 3. Use the Agent

**System Tray Menu** (right-click icon):
- ⚙️ Settings - Change configuration
- 📊 View Logs - See live activity
- 🧪 Run Tests - Execute test suites
- 📁 Open Folders - Quick access to screenshots/logs

**Web Interface**: http://localhost:5555

## Architecture
```
┌─────────────────┐
│  Your Desktop   │
│                 │
│  ┌───────────┐  │
│  │  Agent    │  │──► Selenium (Chrome/Firefox/Edge)
│  │           │  │
│  │  • Web UI │  │◄─► API Server (your company)
│  │  • Tray   │  │
│  │  • Traffic│  │
│  └───────────┘  │
└─────────────────┘
```

## Technical Details

### Technology Stack

- **Python 3.11+**
- **Selenium + Selenium-Wire** - Browser automation & traffic capture
- **Flask** - Web UI server
- **PyStray** - System tray icon
- **PyInstaller** - Executable packaging

### System Requirements

- **OS**: Windows 10+, macOS 10.13+, Linux (Ubuntu 20.04+)
- **RAM**: 2GB minimum, 4GB recommended
- **Browser**: Chrome, Firefox, or Edge installed
- **Network**: Access to API server

### Files & Folders
```
Agent Installation/
├── FormDiscovererAgent(.exe)  # Main executable
├── .env                        # Configuration
├── screenshots/                # Test screenshots
├── logs/                       # Agent logs
│   ├── agent.log
│   └── traffic/                # Browser traffic captures
└── files/                      # Downloaded files
```

## Development

### Setup Development Environment
```bash
# Clone repository
git clone <repo-url>
cd agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env
nano .env  # Edit as needed

# Run in development mode
python main.py
```

### Project Structure
```
agent/
├── main.py                    # Entry point
├── agent_config.py            # Configuration management
├── agent_selenium.py          # Browser automation
├── tray_icon.py               # System tray
├── traffic_capture.py         # Network traffic capture
├── auto_start.py              # Auto-start management
├── web_ui/                    # Web interface
│   ├── server.py              # Flask server
│   ├── templates/             # HTML templates
│   └── static/                # CSS/JS
├── requirements.txt           # Python dependencies
├── FormDiscovererAgent.spec   # PyInstaller config
└── build_installers.sh        # Build script
```

### Building Installers

#### Local Build
```bash
./build_installers.sh
```

#### Docker Build
```bash
./build_in_docker.sh
```

Installers will be in `dist/installers/`

## Configuration

### API Connection
```python
# .env
API_URL=https://api.yourcompany.com
AGENT_TOKEN=your_token_here
COMPANY_ID=1
USER_ID=1
```

### Browser Settings
```python
BROWSER=chrome          # chrome, firefox, or edge
HEADLESS=false          # true for headless mode
```

### Traffic Capture
```python
CAPTURE_TRAFFIC=true    # Enable browser traffic capture
```

When enabled, all HTTP requests/responses are captured during testing. 
Server can request traffic dumps for debugging customer website issues.

### Auto-Start

Enable via Settings UI or manually:

**Windows**: Registry key in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
**macOS**: LaunchAgent plist in `~/Library/LaunchAgents/`
**Linux**: Desktop file in `~/.config/autostart/`

## Troubleshooting

### Agent won't start

1. Check if browser is installed (Chrome/Firefox/Edge)
2. Check logs in `logs/agent.log`
3. Try running in terminal to see errors: `./FormDiscovererAgent`

### Can't connect to API server

1. Verify API_URL in Settings
2. Click "Test Connection" button
3. Check firewall/network settings
4. Contact IT administrator

### System tray icon not appearing

**Linux**: Install tray extension for your desktop environment
**macOS**: Grant accessibility permissions
**Windows**: Check system tray settings

### Browser traffic capture not working

1. Install `selenium-wire`: `pip install selenium-wire`
2. Supported browsers: Chrome, Firefox, Edge
3. Check Settings → Advanced → Capture Traffic

## Security

- **No cloud storage**: All data stays on your network
- **Encrypted communication**: HTTPS to API server
- **Credential management**: Secure token storage
- **Network isolation**: Agent only talks to configured API server

## License

Proprietary - See LICENSE file

## Support

- Documentation: https://docs.formdiscoverer.com
- Email: support@formdiscoverer.com
- Issues: Check logs first (`logs/agent.log`)
