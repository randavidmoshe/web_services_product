# Installer Download Endpoints
# Location: api-server/routes/installer_router.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from pathlib import Path

from models.database import get_db
#from models.user_models import User  # Assuming you have user models

router = APIRouter(prefix="/api/installer", tags=["installer"])

# Path to installers directory
INSTALLERS_DIR = Path(__file__).parent.parent / "installers"

# Supported platforms
PLATFORMS = {
    "windows": "FormDiscovererAgent-2.0.0-Windows.exe",
    "mac": "FormDiscovererAgent-2.0.0-Mac.dmg",
    "mac-zip": "FormDiscovererAgent-2.0.0-Mac.zip",
    "linux": "FormDiscovererAgent-2.0.0-Linux.tar.gz",
    "linux-deb": "FormDiscovererAgent-2.0.0-Linux.deb"
}


@router.get("/download/{platform}")
async def download_installer(
    platform: str,
):
    """
    Download agent installer for specified platform
    
    Platforms:
    - windows: .exe installer
    - mac: .dmg installer
    - mac-zip: .zip for Mac (alternative)
    - linux: .tar.gz archive
    - linux-deb: .deb package for Debian/Ubuntu
    """
    
    # Validate platform
    if platform not in PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform. Supported: {', '.join(PLATFORMS.keys())}"
        )
    
    # Get installer filename
    filename = PLATFORMS[platform]
    filepath = INSTALLERS_DIR / filename
    
    # Check if file exists
    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Installer not available for {platform}"
        )
    
    # Log download (optional)
    # log_installer_download(db, platform, user_id)
    
    # Return file
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/octet-stream'
    )


@router.get("/available")
async def list_available_installers():
    """
    Get list of available installer platforms
    """
    available = {}
    
    for platform, filename in PLATFORMS.items():
        filepath = INSTALLERS_DIR / filename
        available[platform] = {
            "filename": filename,
            "available": filepath.exists(),
            "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2) if filepath.exists() else 0
        }
    
    return {
        "installers": available,
        "version": "2.0.0"
    }


@router.get("/latest-version")
async def get_latest_version():
    """
    Get latest agent version info
    Used by agent for auto-update checks
    """
    return {
        "version": "2.0.0",
        "release_date": "2024-11-16",
        "download_url": "/api/installer/download/",
        "changelog": [
            "Redis/Celery integration for scalability",
            "Direct Redis queue for agent tasks",
            "Improved performance (3x faster)",
            "Support for 100,000+ concurrent agents"
        ]
    }


@router.post("/register-download")
async def register_download(
    download_data: dict,
    db: Session = Depends(get_db)
):
    """
    Track installer downloads (optional)
    """
    platform = download_data.get('platform')
    user_id = download_data.get('user_id')
    company_id = download_data.get('company_id')
    
    # Log to database
    # InstallerDownload.create(db, platform, user_id, company_id)
    
    return {"success": True, "message": "Download registered"}
