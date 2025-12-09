from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/formfinder")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String, unique=True)
    description = Column(Text)
    base_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class SuperAdmin(Base):
    __tablename__ = "super_admins"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password_hash = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)
    # 2FA fields
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    billing_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 2FA enforcement setting
    require_2fa = Column(Boolean, default=False)

class CompanyProductSubscription(Base):
    __tablename__ = "company_product_subscriptions"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    status = Column(String, default="trial")
    is_trial = Column(Boolean, default=True)
    trial_ends_at = Column(DateTime)
    monthly_subscription_cost = Column(Float, default=1000.00)
    monthly_claude_budget = Column(Float, default=500.00)
    claude_used_this_month = Column(Float, default=0.00)
    budget_reset_date = Column(DateTime)
    customer_claude_api_key = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    email = Column(String, unique=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(String, default="user")
    agent_api_token = Column(String, unique=True)
    agent_downloaded_at = Column(DateTime)
    agent_last_active = Column(DateTime)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)
    # 2FA fields
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    # Invitation fields
    invite_token = Column(String(100), unique=True, nullable=True)
    invite_sent_at = Column(DateTime, nullable=True)
    invite_accepted_at = Column(DateTime, nullable=True)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    description = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Network(Base):
    __tablename__ = "networks"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    url = Column(String)
    network_type = Column(String, nullable=False)  # "qa", "staging", or "production"
    # Login credentials for test user (used by crawler)
    login_username = Column(String, nullable=True)
    login_password = Column(String, nullable=True)  # Should be encrypted in production
    login_stages = Column(JSON, default=list)  # Login steps for Form Mapper
    logout_stages = Column(JSON, default=list)  # Logout steps for Form Mapper
    form_pages_use_screenshot_for_button_check = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CrawlSession(Base):
    __tablename__ = "crawl_sessions"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    network_id = Column(Integer, ForeignKey("networks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_instance_id = Column(Integer)
    session_type = Column(String)
    status = Column(String, default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    pages_crawled = Column(Integer, default=0)
    forms_found = Column(Integer, default=0)
    error_message = Column(Text)
    error_code = Column(String(50))  # Machine-readable error code (e.g., PAGE_NOT_FOUND, LOGIN_FAILED)
    created_at = Column(DateTime, default=datetime.utcnow)

class FormPageRoute(Base):
    """
    Stores navigation routes to form pages discovered by the crawler.
    Phase 1: How to reach each form (navigation steps)
    Phase 2 (future): FormPageFields will store field details for each form
    """
    __tablename__ = "form_page_routes"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    network_id = Column(Integer, ForeignKey("networks.id"))
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"))
    
    # Form identification
    form_name = Column(String)  # AI-generated name (e.g., "claim", "expense")
    url = Column(String)  # URL where form appears
    login_url = Column(String)  # Login page URL
    username = Column(String)  # Which test user credentials were used
    
    # Navigation data
    navigation_steps = Column(JSON)  # Array of steps to reach the form
    id_fields = Column(JSON)  # Array of reference field names
    
    # Hierarchy
    parent_form_route_id = Column(Integer, ForeignKey("form_page_routes.id"), nullable=True)
    is_root = Column(Boolean, default=True)
    
    # Verification
    verification_attempts = Column(Integer, default=0)
    last_verified_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("FormPageRoute", remote_side=[id], backref="children")
    
    # Form Mapper relationships  # <-- ADD THESE
    mapper_sessions = relationship("FormMapperSession", back_populates="form_page_route", cascade="all, delete-orphan")
    map_results = relationship("FormMapResult", back_populates="form_page_route", cascade="all, delete-orphan")

class ApiUsage(Base):
    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    subscription_id = Column(Integer, ForeignKey("company_product_subscriptions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"))
    operation_type = Column(String)
    tokens_used = Column(Integer)
    api_cost = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Screenshot(Base):
    __tablename__ = "screenshots"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"))
    form_page_id = Column(Integer, ForeignKey("form_page_routes.id"))  # Updated FK reference
    
    # Image metadata
    filename = Column(String, nullable=False)
    image_type = Column(String, nullable=False)
    description = Column(Text)
    
    # S3 storage
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    s3_url = Column(Text, nullable=False)
    
    # File info
    file_size_bytes = Column(Integer)
    content_type = Column(String, default='image/png')
    width_px = Column(Integer)
    height_px = Column(Integer)
    
    # Metadata
    captured_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class TestTemplate(Base):
    __tablename__ = "test_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # "create_verify", "create_verify_edit_verify"
    display_name = Column(String(200), nullable=False)  # "Create & Verify", "Create, Verify, Edit & Verify"
    test_cases = Column(JSON, nullable=False)  # The JSON array of test cases
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
# Note: Agent model is defined in models/agent_models.py to avoid duplication

# Import related models to resolve relationships
from models.form_mapper_models import FormMapperSession, FormMapResult
