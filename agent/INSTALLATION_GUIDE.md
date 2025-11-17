# Form Discoverer Agent - Installation Guide

## For End Users (Customers)

### Windows

1. **Download**: Get `FormDiscovererAgent-Setup-Windows.exe` from your dashboard
2. **Run Installer**: Double-click the .exe file
3. **Follow Wizard**: Click through installation steps
4. **First Launch**: Agent will open setup wizard in your browser
5. **Configure**: 
   - Enter API server URL (usually provided by your company)
   - Login with your email/password
   - Choose browser (Chrome/Firefox/Edge)
   - Set folder locations
6. **Done**: Agent will appear in system tray (robot icon)

**Auto-start**: Check the option during installation or enable in Settings later.

### macOS

1. **Download**: Get `FormDiscovererAgent-2.0.0-macOS.dmg` from your dashboard
2. **Open DMG**: Double-click the .dmg file
3. **Install**: Drag app to Applications folder
4. **First Launch**: Right-click app → Open (to bypass Gatekeeper)
5. **Configure**: Follow setup wizard in browser
6. **Done**: Agent will appear in menu bar

**Auto-start**: Enable in Settings → Advanced → Auto-start on boot

### Linux

#### Option 1: TAR.GZ (All distributions)
```bash
# Download
wget http://your-api-server.com/api/installer/download/linux

# Extract
tar -xzf FormDiscovererAgent-2.0.0-Linux.tar.gz

# Run
cd FormDiscovererAgent
./FormDiscovererAgent
```

#### Option 2: DEB Package (Debian/Ubuntu)
```bash
# Download
wget http://your-api-server.com/api/installer/download/linux-deb

# Install
sudo dpkg -i FormDiscovererAgent-2.0.0-Linux.deb

# Run
formdiscoverer-agent
```

**Auto-start**: Enable in Settings → Advanced → Auto-start on boot

---

## For Developers

### Building from Source

#### Prerequisites

- Python 3.11+
- pip
- PyInstaller

#### Build Steps
```bash
# Clone repository
git clone <repo-url>
cd agent

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build executable
./build_installers.sh
```

Installers will be in `dist/installers/`

#### Build in Docker (No GUI needed!)
```bash
# Build using Docker
./build_in_docker.sh

# Installers will be in dist/installers/
```

### Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Edit configuration

# Run in development mode
python main.py
```

---

## Troubleshooting

### Windows

**Problem**: "Windows protected your PC" warning
**Solution**: Click "More info" → "Run anyway"

**Problem**: Agent doesn't start
**Solution**: Check if Chrome/Firefox is installed

### macOS

**Problem**: "Cannot open because developer cannot be verified"
**Solution**: Right-click app → Open (first time only)

**Problem**: System tray icon doesn't appear
**Solution**: Grant accessibility permissions in System Preferences

### Linux

**Problem**: `libffi.so.7: cannot open shared object file`
**Solution**: `sudo apt-get install libffi7`

**Problem**: System tray not working
**Solution**: Install system tray extension for your desktop environment

### All Platforms

**Problem**: Can't connect to API server
**Solution**: 
1. Check API URL in Settings
2. Test connection button
3. Check firewall settings
4. Contact your IT administrator

**Problem**: Browser traffic capture not working
**Solution**:
1. Ensure `selenium-wire` is installed
2. Check browser is supported (Chrome/Firefox/Edge)
3. Try disabling and re-enabling in Settings

---

## Configuration

### Environment Variables (.env)
```bash
# API Connection
API_URL=http://localhost:8001
AGENT_TOKEN=agent_abc123...
COMPANY_ID=1
USER_ID=1
AGENT_ID=agent-unique-id

# Browser
BROWSER=chrome
HEADLESS=false

# Folders
SCREENSHOT_FOLDER=/path/to/screenshots
LOG_FOLDER=/path/to/logs
FILES_FOLDER=/path/to/files

# Advanced
POLLING_INTERVAL=2
CAPTURE_TRAFFIC=true
```

### Settings Panel

Access via system tray: Right-click → Settings

Or directly: http://localhost:5555/settings

---

## Uninstallation

### Windows
Control Panel → Programs → Uninstall → Form Discoverer Agent

### macOS
Drag app from Applications to Trash

### Linux (DEB)
```bash
sudo dpkg -r formdiscoverer-agent
```

### Linux (TAR.GZ)
Simply delete the extracted folder

---

## Support

- Email: support@formdiscoverer.com
- Documentation: https://docs.formdiscoverer.com
- System Logs: Check logs folder (Settings → Open Logs Folder)
