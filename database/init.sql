-- Form Discoverer Platform Database Schema
-- PostgreSQL 15+

-- ============================================
-- PRODUCTS (Reference table - 4 products)
-- ============================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) DEFAULT 1000.00,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO products (name, type, description, base_price) VALUES
('Form Page Testing', 'form_testing', 'Discover and analyze form pages', 1000.00),
('Shopping Site Testing', 'shopping_testing', 'E-commerce flow testing', 1500.00),
('Marketing Website Testing', 'marketing_testing', 'Marketing page analysis', 800.00),
('Advancing Websites by AI', 'ai_advancement', 'AI-powered website optimization', 2000.00);


-- ============================================
-- SUPER ADMINS (Platform owner)
-- ============================================
CREATE TABLE super_admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

-- Default super admin (password: admin123)
INSERT INTO super_admins (email, password_hash, name) VALUES
('admin@formfinder.com', '$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i', 'Super Admin');


-- ============================================
-- COMPANIES
-- ============================================
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    billing_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- COMPANY PRODUCT SUBSCRIPTIONS
-- ============================================
CREATE TABLE company_product_subscriptions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    
    -- Subscription status
    status VARCHAR(50) DEFAULT 'trial',  -- 'trial', 'active', 'cancelled', 'expired'
    is_trial BOOLEAN DEFAULT TRUE,
    trial_ends_at TIMESTAMP,
    
    -- Pricing
    monthly_subscription_cost DECIMAL(10,2) NOT NULL DEFAULT 1000.00,
    
    -- Claude API Budget
    monthly_claude_budget DECIMAL(10,2) NOT NULL DEFAULT 500.00,
    claude_used_this_month DECIMAL(10,2) DEFAULT 0.00,
    budget_reset_date DATE DEFAULT CURRENT_DATE + INTERVAL '1 month',
    
    -- Trial: Customer's own API key (encrypted)
    customer_claude_api_key VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(company_id, product_id)
);


-- ============================================
-- USERS (Customer admins and regular users)
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',  -- 'admin', 'user'
    
    -- Agent authentication
    agent_api_token VARCHAR(500) UNIQUE,
    agent_downloaded_at TIMESTAMP,
    agent_last_active TIMESTAMP,
    
    created_by_admin_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);


-- ============================================
-- PROJECTS
-- ============================================
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- NETWORKS (Target websites to test)
-- ============================================
CREATE TABLE networks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    name VARCHAR(255) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    created_by_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- AUTOMATION USERS (Credentials for target sites)
-- ============================================
CREATE TABLE automation_users (
    id SERIAL PRIMARY KEY,
    network_id INTEGER NOT NULL REFERENCES networks(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    password_encrypted VARCHAR(500) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- AGENT INSTANCES (Track connected agents)
-- ============================================
CREATE TABLE agent_instances (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Agent info
    machine_id VARCHAR(255),
    platform VARCHAR(50),  -- 'windows', 'mac', 'linux'
    agent_version VARCHAR(50),
    
    -- Status
    status VARCHAR(50) DEFAULT 'offline',  -- 'online', 'offline', 'running'
    last_heartbeat TIMESTAMP,
    
    connected_at TIMESTAMP DEFAULT NOW(),
    disconnected_at TIMESTAMP
);


-- ============================================
-- CRAWL SESSIONS
-- ============================================
CREATE TABLE crawl_sessions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    project_id INTEGER REFERENCES projects(id),
    network_id INTEGER REFERENCES networks(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    agent_instance_id INTEGER REFERENCES agent_instances(id),
    
    session_type VARCHAR(50) NOT NULL,  -- 'discover_form_pages', 'discover_form_details', etc.
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    pages_crawled INTEGER DEFAULT 0,
    forms_found INTEGER DEFAULT 0,
    
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- FORM PAGES DISCOVERED (Part 1 results)
-- ============================================
CREATE TABLE form_pages_discovered (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    crawl_session_id INTEGER NOT NULL REFERENCES crawl_sessions(id) ON DELETE CASCADE,
    
    url VARCHAR(1000) NOT NULL,
    page_title VARCHAR(500),
    forms_count INTEGER DEFAULT 0,
    screenshot_url VARCHAR(1000),
    
    discovered_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- FORM DETAILS (Part 2 results)
-- ============================================
CREATE TABLE form_details (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    form_page_id INTEGER NOT NULL REFERENCES form_pages_discovered(id) ON DELETE CASCADE,
    
    form_name VARCHAR(255),
    form_action VARCHAR(500),
    form_method VARCHAR(10),
    
    -- JSON data
    fields JSONB,  -- Array of field objects: [{name, type, required, validation}]
    validation_rules JSONB,
    ai_analysis JSONB,  -- Claude's analysis and suggestions
    
    discovered_at TIMESTAMP DEFAULT NOW()
);


-- ============================================
-- API USAGE TRACKING (Claude API calls)
-- ============================================
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    subscription_id INTEGER NOT NULL REFERENCES company_product_subscriptions(id),
    user_id INTEGER REFERENCES users(id),
    crawl_session_id INTEGER REFERENCES crawl_sessions(id),
    
    operation_type VARCHAR(100),  -- 'discover_pages', 'analyze_form', etc.
    tokens_used INTEGER NOT NULL,
    api_cost DECIMAL(10,4) NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_api_usage_company_date ON api_usage(company_id, created_at);
CREATE INDEX idx_api_usage_subscription ON api_usage(subscription_id, created_at);


-- ============================================
-- SCREENSHOTS (Image Storage)
-- ============================================
CREATE TABLE screenshots (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    crawl_session_id INTEGER REFERENCES crawl_sessions(id) ON DELETE CASCADE,
    form_page_id INTEGER REFERENCES form_pages_discovered(id) ON DELETE CASCADE,
    
    -- Image metadata
    filename VARCHAR(255) NOT NULL,
    image_type VARCHAR(50) NOT NULL,  -- 'initial_load', 'after_interaction', 'error', 'form_filled', etc
    description TEXT,
    
    -- S3 storage
    s3_bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    s3_url TEXT NOT NULL,
    
    -- File info
    file_size_bytes INTEGER,
    content_type VARCHAR(100) DEFAULT 'image/png',
    width_px INTEGER,
    height_px INTEGER,
    
    -- Metadata
    captured_at TIMESTAMP DEFAULT NOW(),
    uploaded_by_user_id INTEGER REFERENCES users(id),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_screenshots_company ON screenshots(company_id);
CREATE INDEX idx_screenshots_session ON screenshots(crawl_session_id);
CREATE INDEX idx_screenshots_form_page ON screenshots(form_page_id);
CREATE INDEX idx_screenshots_type ON screenshots(image_type);


-- ============================================
-- INDEXES for performance
-- ============================================
CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_projects_company_product ON projects(company_id, product_id);
CREATE INDEX idx_crawl_sessions_user ON crawl_sessions(user_id);
CREATE INDEX idx_crawl_sessions_status ON crawl_sessions(status);
CREATE INDEX idx_form_pages_session ON form_pages_discovered(crawl_session_id);


-- ============================================
-- SAMPLE DATA for testing
-- ============================================

-- Sample Company
INSERT INTO companies (name, billing_email) VALUES
('Acme Corporation', 'billing@acme.com');

-- Sample Subscription (Company 1, Product 1 - Form Testing)
INSERT INTO company_product_subscriptions (
    company_id, product_id, status, is_trial, 
    monthly_subscription_cost, monthly_claude_budget
) VALUES (1, 1, 'active', FALSE, 1000.00, 500.00);

-- Sample Customer Admin
INSERT INTO users (company_id, email, password_hash, name, role) VALUES
(1, 'admin@acme.com', '$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i', 'John Admin', 'admin');

-- Sample Regular User (password: user123)
INSERT INTO users (company_id, email, password_hash, name, role, created_by_admin_id) VALUES
(1, 'user@acme.com', '$2b$12$p7hbvVi9UJVAxdXQsai0e.xya7GZx0lKsACDn.rC3P7PXB0hwte5i', 'Jane User', 'user', 2);

-- Sample Project (created by admin user ID 2)
INSERT INTO projects (company_id, product_id, name, description, created_by_user_id) VALUES
(1, 1, 'E-commerce Testing', 'Test our online store forms', 2);

-- Sample Network (created by admin user ID 2)
INSERT INTO networks (project_id, company_id, product_id, name, url, created_by_user_id) VALUES
(1, 1, 1, 'Production Site', 'https://shop.acme.com', 2);
