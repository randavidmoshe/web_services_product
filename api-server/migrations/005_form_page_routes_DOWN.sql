-- Migration 005: Form Page Routes
-- DOWN migration - Rollback to form_pages_discovered
-- Location: web_services_product/api-server/migrations/005_form_page_routes_DOWN.sql

-- ========== STEP 1: Drop indexes ==========
DROP INDEX IF EXISTS idx_form_page_routes_company_id;
DROP INDEX IF EXISTS idx_form_page_routes_project_id;
DROP INDEX IF EXISTS idx_form_page_routes_network_id;
DROP INDEX IF EXISTS idx_form_page_routes_crawl_session_id;
DROP INDEX IF EXISTS idx_form_page_routes_form_name;
DROP INDEX IF EXISTS idx_form_page_routes_parent_id;
DROP INDEX IF EXISTS idx_form_page_routes_is_root;

-- ========== STEP 2: Remove foreign key from screenshots ==========
ALTER TABLE screenshots 
DROP CONSTRAINT IF EXISTS screenshots_form_page_id_fkey;

-- ========== STEP 3: Remove self-referencing foreign key ==========
ALTER TABLE form_page_routes
DROP CONSTRAINT IF EXISTS fk_parent_form_route;

-- ========== STEP 4: Restore original columns ==========
ALTER TABLE form_page_routes
ADD COLUMN IF NOT EXISTS page_title VARCHAR(255),
ADD COLUMN IF NOT EXISTS forms_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS screenshot_url VARCHAR(500);

-- Rename column back
ALTER TABLE form_page_routes 
RENAME COLUMN created_at TO discovered_at;

-- ========== STEP 5: Drop new columns ==========
ALTER TABLE form_page_routes
DROP COLUMN IF EXISTS project_id,
DROP COLUMN IF EXISTS network_id,
DROP COLUMN IF EXISTS form_name,
DROP COLUMN IF EXISTS login_url,
DROP COLUMN IF EXISTS username,
DROP COLUMN IF EXISTS navigation_steps,
DROP COLUMN IF EXISTS id_fields,
DROP COLUMN IF EXISTS parent_form_route_id,
DROP COLUMN IF EXISTS is_root,
DROP COLUMN IF EXISTS verification_attempts,
DROP COLUMN IF EXISTS last_verified_at,
DROP COLUMN IF EXISTS updated_at;

-- ========== STEP 6: Rename table back ==========
ALTER TABLE form_page_routes RENAME TO form_pages_discovered;

-- ========== STEP 7: Re-add foreign key from screenshots ==========
ALTER TABLE screenshots
ADD CONSTRAINT screenshots_form_page_id_fkey 
FOREIGN KEY (form_page_id) 
REFERENCES form_pages_discovered(id) 
ON DELETE SET NULL;

-- ========== STEP 8: Remove login credentials from networks ==========
ALTER TABLE networks
DROP COLUMN IF EXISTS login_username,
DROP COLUMN IF EXISTS login_password;
