from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import routes
from routes import auth, agent, projects, crawl, screenshots
from routes import agent_router
from routes import installer_router
from models.database import engine, Base
from services.s3_storage import create_s3_bucket_if_not_exists

load_dotenv()

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting API Server...")
    print("📊 Database connection ready")
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
    allow_origins=["http://localhost:3000"],  # Web app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["crawl"])
app.include_router(screenshots.router, prefix="/api/screenshots", tags=["screenshots"])
app.include_router(agent_router.router)
app.include_router(installer_router.router)

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
