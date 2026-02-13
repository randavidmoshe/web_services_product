from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
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

    # Password reset fields
    password_reset_token_hash = Column(String(64), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    # Token invalidation (for logout all devices)
    token_version = Column(Integer, default=1)


class SuperAdminAuditLog(Base):
    __tablename__ = "super_admin_audit_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("super_admins.id"), nullable=False)
    action = Column(String(50), nullable=False)
    target_company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    billing_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 2FA enforcement setting
    require_2fa = Column(Boolean, default=False)
    form_mapper_config = Column(JSON, default=dict)
    kms_key_arn = Column(String(255), nullable=True)  # BYOK - Customer's KMS key ARN
    debug_mode = Column(Boolean, default=False)  # Enable verbose AI logging for debugging

    # Onboarding fields
    account_category = Column(String(20), nullable=True)  # 'form_centric' | 'dynamic' | NULL
    access_model = Column(String(20), nullable=True)  # 'byok' | 'early_access' | NULL
    access_status = Column(String(20), default='pending')  # 'active' | 'pending' | 'rejected'
    onboarding_completed = Column(Boolean, default=False)
    # Early Access trial limits
    daily_ai_budget = Column(Float, default=10.00)  # $ per day for Early Access
    trial_days_total = Column(Integer, default=10)  # Total trial days
    trial_start_date = Column(DateTime, nullable=True)  # When Early Access approved
    ai_used_today = Column(Float, default=0.00)  # Reset daily
    last_usage_reset_date = Column(DateTime, nullable=True)  # For daily reset tracking

class CompanyProductSubscription(Base):
    __tablename__ = "company_product_subscriptions"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
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
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
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

    # Email verification fields (for self-signup)
    is_verified = Column(Boolean, default=False)
    email_verification_token_hash = Column(String(64), nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)

    # Password reset fields
    password_reset_token_hash = Column(String(64), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    # Token invalidation (for logout all devices)
    token_version = Column(Integer, default=1)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    description = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    form_mapper_config = Column(JSON, default=dict)  # Per-project config overrides
    project_type = Column(String(50), default='enterprise')  # 'enterprise' or 'dynamic_content'

class Network(Base):
    __tablename__ = "networks"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String)
    url = Column(String)
    network_type = Column(String, nullable=False)  # "qa", "staging", or "production"
    # Login credentials for test user (used by crawler)
    login_username = Column(Text, nullable=True)  # Encrypted
    login_password = Column(Text, nullable=True)  # Encrypted
    totp_secret = Column(Text, nullable=True)  # Encrypted TOTP secret for 2FA
    login_hints = Column(Text, nullable=True)  # AI guidance notes for login automation
    login_stages = Column(JSON, default=list)  # Login steps for Form Mapper
    logout_stages = Column(JSON, default=list)  # Logout steps for Form Mapper
    dashboard_url = Column(String, nullable=True)  # Captured after successful login mapping
    form_pages_use_screenshot_for_button_check = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CrawlSession(Base):
    __tablename__ = "crawl_sessions"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    network_id = Column(Integer, ForeignKey("networks.id"))
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    agent_instance_id = Column(Integer)
    session_type = Column(String)
    status = Column(String, default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    pages_crawled = Column(Integer, default=0)
    forms_found = Column(Integer, default=0)
    error_message = Column(Text)
    error_code = Column(String(50))  # Machine-readable error code (e.g., PAGE_NOT_FOUND, LOGIN_FAILED)
    mapper_session_id = Column(Integer, nullable=True)  # FormMapperSession ID when login mapping runs before discovery
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    mapping_hints = Column(Text, nullable=True)  # AI guidance notes for form mapping
    
    # Navigation data
    navigation_steps = Column(JSON)  # Array of steps to reach the form
    id_fields = Column(JSON)  # Array of reference field names

    parent_fields = Column(JSON)  # Full parent reference field objects from AI
    
    # Hierarchy
    parent_form_route_id = Column(Integer, ForeignKey("form_page_routes.id"), nullable=True)
    is_root = Column(Boolean, default=True)

    # User-provided inputs for form mapping (mandatory values AI can't guess)
    user_provided_inputs = Column(JSON, nullable=True)
    user_provided_inputs_raw = Column(Text, nullable=True)

    # Spec document for compliance checking
    spec_document = Column(JSON, nullable=True)  # {filename, content_type, uploaded_at}
    spec_document_content = Column(Text, nullable=True)  # Actual text content

    # Verification Instructions (for AI visual verification during mapping)
    verification_file = Column(JSON, nullable=True)  # {filename, s3_key, content_type, status}
    verification_file_content = Column(Text, nullable=True)  # Extracted text from file

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
    test_scenarios = relationship("FormPageTestScenario", back_populates="form_page_route", cascade="all, delete-orphan")


class ProjectFormHierarchy(Base):
    """
    Stores parent-child relationships between form types at project level.
    Built by AI after form discovery completes.
    """
    __tablename__ = "project_form_hierarchy"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    form_id = Column(Integer, ForeignKey("form_page_routes.id"), nullable=False)
    form_name = Column(String, nullable=False)
    parent_form_id = Column(Integer, ForeignKey("form_page_routes.id"), nullable=True)
    parent_form_name = Column(String, nullable=True)  # NULL = root form
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"), index=True)
    form_page_id = Column(Integer, ForeignKey("form_page_routes.id"), index=True)  # Updated FK reference
    
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

class ActivityLogEntry(Base):
    """
    Stores activity log entries from agent.
    Used by Discovery, Mapping, and Test Runs.
    """
    __tablename__ = "activity_log_entries"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Activity identification
    activity_type = Column(String(50), nullable=False, index=True)  # 'discovery', 'mapping', 'test_run'

    # Link to specific session (only one will be set)
    crawl_session_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=True, index=True)
    mapper_session_id = Column(Integer, ForeignKey("form_mapper_sessions.id"), nullable=True, index=True)
    test_run_id = Column(Integer, nullable=True, index=True)  # Future: ForeignKey to test_runs

    # Log entry data
    timestamp = Column(DateTime, nullable=False, index=True)  # When event occurred on agent
    level = Column(String(20), nullable=False)  # 'info', 'warning', 'error'
    category = Column(String(50), default='milestone')  # 'milestone' or 'debug'
    message = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)  # Optional structured data

    # Server timestamp
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# S3 File Tracking Tables
# ============================================================================

class ActivityScreenshot(Base):
    """Track screenshots uploaded to S3 for activity sessions."""
    __tablename__ = "activity_screenshots"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    activity_type = Column(String(50), nullable=False)  # 'mapping', 'test_run'
    session_id = Column(Integer, nullable=False)  # mapper_session_id or test_run_id
    s3_key = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Index for fast lookups
    __table_args__ = (
        Index('ix_activity_screenshots_session', 'activity_type', 'session_id'),
        Index('ix_activity_screenshots_company_project', 'company_id', 'project_id'),
    )


class FormUploadedFile(Base):
    """Track files uploaded during form mapping (e.g., resume.pdf for file upload fields)."""
    __tablename__ = "form_uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    form_page_route_id = Column(Integer, ForeignKey("form_page_routes.id"), nullable=False)
    form_map_result_id = Column(Integer, ForeignKey("form_map_results.id"), nullable=True)
    path_number = Column(Integer, nullable=True)
    s3_key = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    field_name = Column(String(255), nullable=True)  # Which form field this file is for
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_form_uploaded_files_route', 'form_page_route_id'),
    )


class EmailVerificationRateLimit(Base):
    """Track verification email sends for rate limiting"""
    __tablename__ = "email_verification_rate_limits"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('ix_email_verification_rate_limits_email_sent', 'email', 'sent_at'),
    )

# ============================================================================
# Session & Security Tables
# ============================================================================

class UserSession(Base):
    """Track active user sessions for session management and logout all devices."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)

    __table_args__ = (
        Index('ix_user_sessions_user_id', 'user_id'),
        Index('ix_user_sessions_refresh_hash', 'refresh_token_hash'),
    )


class LoginAttempt(Base):
    """Track login attempts for rate limiting and security audit."""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    success = Column(Boolean, default=False)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_login_attempts_email_time', 'email', 'attempted_at'),
        Index('ix_login_attempts_ip_time', 'ip_address', 'attempted_at'),
    )

# Import related models to resolve relationships
from models.form_mapper_models import FormMapperSession, FormMapResult
from models.test_page_models import TestPageRoute
