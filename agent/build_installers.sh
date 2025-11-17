#!/bin/bash
# Build installers for all platforms
# Updated for web-based UI

set -e  # Exit on error

echo "=========================================="
echo "Form Discoverer Agent - Build Installers"
echo "Version: 2.0.0"
echo "=========================================="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo ""
echo "Building executable with PyInstaller..."
pyinstaller FormDiscovererAgent.spec --clean

# Create installers directory
mkdir -p dist/installers

# Detect platform and build appropriate installer
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Creating Linux installer..."
    
    # Create tar.gz
    cd dist
    tar -czf installers/FormDiscovererAgent-2.0.0-Linux.tar.gz FormDiscovererAgent
    cd ..
    
    # Optionally create .deb package (requires dpkg)
    if command -v dpkg-deb &> /dev/null; then
        echo "Creating .deb package..."
        mkdir -p dist/deb/DEBIAN
        mkdir -p dist/deb/usr/local/bin
        mkdir -p dist/deb/usr/share/applications
        
        # Copy executable
        cp dist/FormDiscovererAgent dist/deb/usr/local/bin/
        
        # Create control file
        cat > dist/deb/DEBIAN/control << EOF
Package: formdiscoverer-agent
Version: 2.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Form Discoverer <support@formdiscoverer.com>
Description: Form Discoverer Agent
 AI-powered web testing agent
EOF
        
        # Create .desktop file
        cat > dist/deb/usr/share/applications/formdiscoverer-agent.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Form Discoverer Agent
Comment=AI-powered web testing
Exec=/usr/local/bin/FormDiscovererAgent
Icon=formdiscoverer
Terminal=false
Categories=Development;
EOF
        
        # Build package
        dpkg-deb --build dist/deb dist/installers/FormDiscovererAgent-2.0.0-Linux.deb
        rm -rf dist/deb
    fi
    
    echo "✓ Linux installer created: dist/installers/FormDiscovererAgent-2.0.0-Linux.tar.gz"
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "Creating macOS installer..."
    
    # Create .app bundle
    mkdir -p "dist/FormDiscovererAgent.app/Contents/MacOS"
    mkdir -p "dist/FormDiscovererAgent.app/Contents/Resources"
    
    # Copy executable
    cp dist/FormDiscovererAgent "dist/FormDiscovererAgent.app/Contents/MacOS/"
    
    # Create Info.plist
    cat > "dist/FormDiscovererAgent.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>FormDiscovererAgent</string>
    <key>CFBundleIdentifier</key>
    <string>com.formdiscoverer.agent</string>
    <key>CFBundleName</key>
    <string>Form Discoverer Agent</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF
    
    # Create DMG (requires create-dmg tool)
    if command -v create-dmg &> /dev/null; then
        create-dmg \
            --volname "Form Discoverer Agent" \
            --window-pos 200 120 \
            --window-size 800 400 \
            --icon-size 100 \
            --app-drop-link 600 185 \
            "dist/installers/FormDiscovererAgent-2.0.0-macOS.dmg" \
            "dist/FormDiscovererAgent.app"
    else
        # Fallback: create zip
        cd dist
        zip -r installers/FormDiscovererAgent-2.0.0-macOS.zip FormDiscovererAgent.app
        cd ..
    fi
    
    echo "✓ macOS installer created"
    
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo ""
    echo "Creating Windows installer..."
    
    # Check if Inno Setup is installed
    if command -v iscc &> /dev/null; then
        iscc installer_windows.iss
        echo "✓ Windows installer created: dist/installers/FormDiscovererAgent-Setup-Windows.exe"
    else
        echo "⚠ Inno Setup not found. Creating zip instead..."
        cd dist
        7z a installers/FormDiscovererAgent-2.0.0-Windows.zip FormDiscovererAgent.exe
        cd ..
    fi
fi

echo ""
echo "=========================================="
echo "Build complete!"
echo "=========================================="
ls -lh dist/installers/
echo ""
echo "Installers are in: dist/installers/"
