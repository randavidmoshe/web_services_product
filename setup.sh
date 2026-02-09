#!/bin/bash
# Setup script - generates all project files

echo "🚀 Setting up Form Discoverer Platform..."

# Create directory structure
mkdir -p api-server/routes
mkdir -p api-server/services/{part1,part2,claude_api}
mkdir -p api-server/middleware
mkdir -p web-app/app/{auth,dashboard,admin,api}
mkdir -p agent/crawler

# API Routes files
cat > api-server/routes/__init__.py << 'EOF'
# Routes package
EOF

cat > api-server/routes/auth.py << 'EOF'
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db, User, SuperAdmin
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")

@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    # Check super admin
    admin = db.query(SuperAdmin).filter(SuperAdmin.email == email).first()
    if admin and pwd_context.verify(password, admin.password_hash):
        return {"token": create_token({"user_id": admin.id, "type": "super_admin"}), "type": "super_admin"}
    
    # Check regular user
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):
        user.last_login_at = datetime.utcnow()
        db.commit()
        return {"token": create_token({"user_id": user.id, "type": "user"}), "type": "user"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
EOF

cat > api-server/routes/agent_web.py << 'EOF'
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from models.database import get_db, User
import secrets

router = APIRouter()

@router.post("/generate-token")
async def generate_agent_token(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    if not user.agent_api_token:
        user.agent_api_token = secrets.token_urlsafe(32)
        db.commit()
    
    return {"token": user.agent_api_token}

@router.post("/validate")
async def validate_token(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.agent_api_token == token).first()
    if not user:
        raise HTTPException(401, "Invalid token")
    
    return {
        "user_id": user.id,
        "company_id": user.company_id,
        "email": user.email
    }

@router.get("/commands")
async def get_commands(authorization: str = Header(None), db: Session = Depends(get_db)):
    # Parse token from "Bearer TOKEN"
    token = authorization.replace("Bearer ", "") if authorization else None
    user = db.query(User).filter(User.agent_api_token == token).first()
    if not user:
        raise HTTPException(401, "Invalid token")
    
    # TODO: Return pending commands for this user
    return []
EOF

cat > api-server/routes/projects.py << 'EOF'
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db, Project

router = APIRouter()

@router.get("/")
async def list_projects(company_id: int, db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.company_id == company_id).all()
    return projects

@router.post("/")
async def create_project(name: str, company_id: int, product_id: int, user_id: int, db: Session = Depends(get_db)):
    project = Project(
        name=name,
        company_id=company_id,
        product_id=product_id,
        created_by_user_id=user_id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
EOF

cat > api-server/routes/crawl.py << 'EOF'
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db, CrawlSession
from datetime import datetime

router = APIRouter()

@router.post("/discover-forms")
async def discover_forms(
    project_id: int,
    network_id: int, 
    user_id: int,
    company_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    # Create crawl session
    session = CrawlSession(
        company_id=company_id,
        product_id=product_id,
        project_id=project_id,
        network_id=network_id,
        user_id=user_id,
        session_type="discover_form_pages",
        status="pending"
    )
    db.add(session)
    db.commit()
    
    return {"session_id": session.id, "status": "pending", "message": "Crawl session created"}
EOF

# Agent files
cat > agent/requirements.txt << 'EOF'
selenium==4.15.2
requests==2.31.0
python-dotenv==1.0.0
webdriver-manager==4.0.1
EOF

cat > agent/main.py << 'EOF'
import json
import os
import time
import requests
from pathlib import Path

CONFIG_FILE = "agent_config.json"

def first_time_setup():
    print("=== Form Discoverer Agent Setup ===\n")
    print("Please enter your agent token from the web application:")
    token = input("Token: ").strip()
    email = input("Email: ").strip()
    api_url = input("API URL [http://localhost:8000]: ").strip() or "http://localhost:8000"
    
    # Validate
    response = requests.post(f"{api_url}/api/agent/validate", json={"token": token})
    if response.status_code == 200:
        data = response.json()
        config = {
            "api_url": api_url,
            "user_token": token,
            "user_id": data["user_id"],
            "user_email": email,
            "company_id": data["company_id"]
        }
        Path(CONFIG_FILE).write_text(json.dumps(config, indent=2))
        print("\n✅ Agent configured successfully!")
        return config
    else:
        print("\n❌ Invalid token")
        exit(1)

def load_config():
    if not Path(CONFIG_FILE).exists():
        return first_time_setup()
    return json.loads(Path(CONFIG_FILE).read_text())

def main():
    config = load_config()
    print(f"\n🤖 Agent running for: {config['user_email']}")
    print(f"📡 API: {config['api_url']}")
    print(f"⏳ Waiting for commands...\n")
    
    while True:
        try:
            # Poll for commands
            response = requests.get(
                f"{config['api_url']}/api/agent/commands",
                headers={"Authorization": f"Bearer {config['user_token']}"}
            )
            
            if response.status_code == 200:
                commands = response.json()
                for cmd in commands:
                    print(f"📨 Received command: {cmd.get('type')}")
                    # TODO: Execute command
                    
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n👋 Agent stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
EOF

cat > agent/README.md << 'EOF'
# Agent Application

## Setup
```bash
pip install -r requirements.txt
python main.py
```

## Integration Points

### Add Your Selenium Code
Place your crawling code in `crawler/` directory.

See crawler/README.md for details.
EOF

cat > agent/crawler/README.md << 'EOF'
# Crawler Module

## TODO: Add Your Selenium Code Here

Your selenium crawling code should go in this directory.

Example structure:
- selenium_wrapper.py - Your main Selenium code
- dom_extractor.py - DOM extraction logic
- form_detector.py - Form detection logic
EOF

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Add your Claude API key to .env"
echo "3. Run: docker-compose up"
echo "4. In another terminal: cd agent && python main.py"
EOF

chmod +x /home/claude/form-discoverer-platform/setup.sh
