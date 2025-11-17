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

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    billing_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

class FormPageDiscovered(Base):
    __tablename__ = "form_pages_discovered"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"))
    url = Column(String)
    page_title = Column(String)
    forms_count = Column(Integer, default=0)
    screenshot_url = Column(String)
    discovered_at = Column(DateTime, default=datetime.utcnow)

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
    form_page_id = Column(Integer, ForeignKey("form_pages_discovered.id"))
    
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

