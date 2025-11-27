-- Migration 005: Form Page Routes
-- UP migration - Transforms form_pages_discovered to form_page_routes
-- Location: web_services_product/api-server/migrations/005_form_page_routes_UP.sql

-- ========== STEP 1: Add login credentials to networks table ==========
ALTER TABLE networks 
ADD COLUMN IF NOT EXISTS login_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS login_password VARCHAR(255);

COMMENT ON COLUMN networks.login_username IS 'Test user username for crawler login';
COMMENT ON COLUMN networks.login_password IS 'Test user password for crawler login (should be encrypted)';

-- ========== STEP 2: Rename and transform form_pages_discovered ==========

-- First, drop the foreign key constraint from screenshots if it exists
ALTER TABLE screenshots 
DROP CONSTRAINT IF EXISTS screenshots_form_page_id_fkey;

-- Rename the table
ALTER TABLE form_pages_discovered RENAME TO form_page_routes;

-- Add new columns
ALTER TABLE form_page_routes
ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id),
ADD COLUMN IF NOT EXISTS network_id INTEGER REFERENCES networks(id),
ADD COLUMN IF NOT EXISTS form_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS login_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS username VARCHAR(255),
ADD COLUMN IF NOT EXISTS navigation_steps JSONB,
ADD COLUMN IF NOT EXISTS id_fields JSONB,
ADD COLUMN IF NOT EXISTS parent_form_route_id INTEGER,
ADD COLUMN IF NOT EXISTS is_root BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS verification_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Rename existing columns to match new schema
ALTER TABLE form_page_routes 
RENAME COLUMN discovered_at TO created_at;

-- Drop columns that are no longer needed
ALTER TABLE form_page_routes
DROP COLUMN IF EXISTS page_title,
DROP COLUMN IF EXISTS forms_count,
DROP COLUMN IF EXISTS screenshot_url;

-- Add self-referencing foreign key for parent hierarchy
ALTER TABLE form_page_routes
ADD CONSTRAINT fk_parent_form_route 
FOREIGN KEY (parent_form_route_id) 
REFERENCES form_page_routes(id) 
ON DELETE SET NULL;

-- Re-add foreign key from screenshots to the renamed table
ALTER TABLE screenshots
ADD CONSTRAINT screenshots_form_page_id_fkey 
FOREIGN KEY (form_page_id) 
REFERENCES form_page_routes(id) 
ON DELETE SET NULL;

-- ========== STEP 3: Create indexes ==========
CREATE INDEX IF NOT EXISTS idx_form_page_routes_company_id ON form_page_routes(company_id);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_project_id ON form_page_routes(project_id);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_network_id ON form_page_routes(network_id);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_crawl_session_id ON form_page_routes(crawl_session_id);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_form_name ON form_page_routes(form_name);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_parent_id ON form_page_routes(parent_form_route_id);
CREATE INDEX IF NOT EXISTS idx_form_page_routes_is_root ON form_page_routes(is_root);

-- ========== STEP 4: Add comments ==========
COMMENT ON TABLE form_page_routes IS 'Navigation routes to form pages discovered by crawler (Phase 1)';
COMMENT ON COLUMN form_page_routes.form_name IS 'AI-generated semantic name for the form';
COMMENT ON COLUMN form_page_routes.navigation_steps IS 'JSON array of Selenium steps to reach this form';
COMMENT ON COLUMN form_page_routes.id_fields IS 'JSON array of reference field names (for hierarchy)';
COMMENT ON COLUMN form_page_routes.parent_form_route_id IS 'Self-reference to parent form in hierarchy';
COMMENT ON COLUMN form_page_routes.is_root IS 'True if form has no parent dependencies';
COMMENT ON COLUMN form_page_routes.verification_attempts IS 'Number of times navigation path was verified';
