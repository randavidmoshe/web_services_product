from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import routes
#from routes import auth, agent, projects, crawl_DEPRECATED, screenshots
from routes import auth, agent, projects, screenshots
from routes import agent_router
from routes import installer_router
from models.database import engine, Base, SessionLocal, SuperAdmin
from services.s3_storage import create_s3_bucket_if_not_exists
from routes import form_pages
from passlib.context import CryptContext

load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_super_admin_if_not_exists():
    """
    Create super admin from environment variables if not exists.
    This ensures no hardcoded passwords in SQL files.
    
    Required environment variables for production:
    - SUPER_ADMIN_EMAIL: Admin email address
    - SUPER_ADMIN_PASSWORD: Admin password (plain text, will be hashed)
    """
    db = SessionLocal()
    try:
        admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@formfinder.com")
        admin_password = os.getenv("SUPER_ADMIN_PASSWORD")
        admin_name = os.getenv("SUPER_ADMIN_NAME", "Super Admin")
        
        # Check if super admin already exists
        existing = db.query(SuperAdmin).filter(SuperAdmin.email == admin_email).first()
        if existing:
            print(f"✅ Super admin already exists: {admin_email}")
            return
        
        # In production, password MUST be set via environment variable
        if not admin_password:
            # Development fallback - ONLY for local development
            if os.getenv("ENVIRONMENT", "development") == "production":
                print("❌ ERROR: SUPER_ADMIN_PASSWORD not set in production!")
                print("   Set SUPER_ADMIN_PASSWORD environment variable.")
                return
            else:
                print("⚠️  WARNING: Using default password for development only!")
                admin_password = "admin123"  # Development only
        
        # Create super admin
        admin = SuperAdmin(
            email=admin_email,
            password_hash=pwd_context.hash(admin_password),
            name=admin_name
        )
        db.add(admin)
        db.commit()
        print(f"✅ Created super admin: {admin_email}")
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        db.rollback()
    finally:
        db.close()

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting API Server...")
    print("📊 Database connection ready")
    print("👤 Checking super admin...")
    create_super_admin_if_not_exists()
    print("📦 Checking S3 bucket...")
    create_s3_bucket_if_not_exists()
    yield
    # Shutdown
    print("👋 Shutting down API Server...")

app = FastAPI(
    title="Form Discoverer API",
    description="AI-powered form discovery and testing platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Web app (dashboard)
        "http://localhost:3001",   # Marketing site
        "https://localhost",       # HTTPS local
        "https://www.quathera.com",
        "https://app.quathera.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
#app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(screenshots.router, prefix="/api/screenshots", tags=["screenshots"])
app.include_router(agent_router.router)
app.include_router(installer_router.router)
app.include_router(form_pages.router, prefix="/api/form-pages", tags=["form-pages"])

@app.get("/")
async def root():
    return {
        "message": "Form Discoverer API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
