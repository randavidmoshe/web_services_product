-- Migration 007: Scalability indexes for Form Mapper
-- Optimized for hundreds of thousands of concurrent users

-- ============================================================
-- API USAGE INDEXES (for budget tracking at scale)
-- ============================================================

-- Fast budget lookups by company+product
CREATE INDEX IF NOT EXISTS idx_api_usage_company_product 
ON api_usage(company_id, product_id);

-- Time-range queries for usage reports
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at 
ON api_usage(created_at DESC);

-- Combined index for monthly usage calculations
CREATE INDEX IF NOT EXISTS idx_api_usage_company_product_date 
ON api_usage(company_id, product_id, created_at DESC);

-- Operation type filtering
CREATE INDEX IF NOT EXISTS idx_api_usage_operation_type 
ON api_usage(operation_type);

-- ============================================================
-- FORM MAPPER SESSION INDEXES
-- ============================================================

-- Active sessions by company
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_company_status 
ON form_mapper_sessions(company_id, status);

-- User's sessions
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_user 
ON form_mapper_sessions(user_id, created_at DESC);

-- Session lookup by form_route
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_form_route 
ON form_mapper_sessions(form_route_id);

-- Recent sessions (for monitoring)
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_created 
ON form_mapper_sessions(created_at DESC);

-- ============================================================
-- FORM MAP RESULTS INDEXES
-- ============================================================

-- Results by form route
CREATE INDEX IF NOT EXISTS idx_form_map_results_form_route 
ON form_map_results(form_route_id);

-- Results by company
CREATE INDEX IF NOT EXISTS idx_form_map_results_company 
ON form_map_results(company_id, created_at DESC);

-- ============================================================
-- FORM PAGE ROUTES INDEXES
-- ============================================================

-- Routes by network (for navigation loading)
CREATE INDEX IF NOT EXISTS idx_form_page_routes_network 
ON form_page_routes(network_id);

-- Routes by project
CREATE INDEX IF NOT EXISTS idx_form_page_routes_project 
ON form_page_routes(project_id);

-- Root routes only
CREATE INDEX IF NOT EXISTS idx_form_page_routes_root 
ON form_page_routes(company_id, is_root) WHERE is_root = true;

-- ============================================================
-- NETWORKS INDEXES
-- ============================================================

-- Networks by project
CREATE INDEX IF NOT EXISTS idx_networks_project 
ON networks(project_id);

-- Networks by company
CREATE INDEX IF NOT EXISTS idx_networks_company 
ON networks(company_id);

-- ============================================================
-- SUBSCRIPTION INDEXES (for budget checks)
-- ============================================================

-- Fast subscription lookup for budget checks
CREATE INDEX IF NOT EXISTS idx_subscriptions_company_product_status 
ON company_product_subscriptions(company_id, product_id, status);

-- Budget reset date for batch processing
CREATE INDEX IF NOT EXISTS idx_subscriptions_budget_reset 
ON company_product_subscriptions(budget_reset_date);

-- ============================================================
-- USERS INDEXES
-- ============================================================

-- Users by company
CREATE INDEX IF NOT EXISTS idx_users_company 
ON users(company_id);

-- Agent token lookup (fast auth)
CREATE INDEX IF NOT EXISTS idx_users_agent_token 
ON users(agent_api_token) WHERE agent_api_token IS NOT NULL;

-- ============================================================
-- CRAWL SESSIONS INDEXES
-- ============================================================

-- Sessions by network
CREATE INDEX IF NOT EXISTS idx_crawl_sessions_network 
ON crawl_sessions(network_id, created_at DESC);

-- Active sessions
CREATE INDEX IF NOT EXISTS idx_crawl_sessions_status 
ON crawl_sessions(status, created_at DESC);

-- ============================================================
-- PARTIAL INDEXES (for common queries)
-- ============================================================

-- Active subscriptions only
CREATE INDEX IF NOT EXISTS idx_subscriptions_active 
ON company_product_subscriptions(company_id, product_id) 
WHERE status IN ('active', 'trial');

-- Pending/running mapper sessions
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_active 
ON form_mapper_sessions(company_id, user_id) 
WHERE status IN ('pending', 'running', 'logging_in', 'navigating', 'mapping');

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON INDEX idx_api_usage_company_product IS 'Fast budget lookups - used on every AI call';
COMMENT ON INDEX idx_subscriptions_company_product_status IS 'Critical for budget checks at scale';
COMMENT ON INDEX idx_form_mapper_sessions_active IS 'Active session monitoring and limits';
