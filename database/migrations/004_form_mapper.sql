-- ============================================================================
-- Migration: 004_form_mapper.sql
-- Description: Add tables for Form Mapper feature
-- Date: 2025-12-01
-- ============================================================================

-- ============================================================================
-- TABLE: form_mapper_sessions
-- Tracks each form mapping session
-- ============================================================================
CREATE TABLE IF NOT EXISTS form_mapper_sessions (
    id SERIAL PRIMARY KEY,
    
    -- Link to discovered form page (from Form Pages Locator)
    form_page_route_id INTEGER REFERENCES form_page_routes(id) ON DELETE CASCADE NOT NULL,
    
    -- Ownership
    network_id INTEGER REFERENCES networks(id) ON DELETE SET NULL,
    company_id INTEGER,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Agent assignment
    agent_id VARCHAR(100),
    
    -- Session configuration (JSON)
    -- Contains: browser, headless, enable_ui_verification, use_full_dom,
    --           max_retries, enable_junction_discovery, max_junction_paths, test_cases
    config JSONB DEFAULT '{}'::jsonb,
    
    -- State machine status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- Valid statuses:
    --   pending, initializing, extracting_dom, generating_steps,
    --   executing, recovering, regenerating, verifying_ui,
    --   completing, completed, failed, cancelled
    
    -- Progress tracking
    current_step_index INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    steps_executed INTEGER DEFAULT 0,
    
    -- Junction discovery tracking
    current_path_number INTEGER DEFAULT 1,
    total_paths_discovered INTEGER DEFAULT 0,
    
    -- Error tracking
    consecutive_failures INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- AI budget tracking
    ai_calls_count INTEGER DEFAULT 0,
    ai_tokens_used INTEGER DEFAULT 0,
    ai_cost_estimate DECIMAL(10, 4) DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for form_mapper_sessions
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_status 
    ON form_mapper_sessions(status);
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_user_id 
    ON form_mapper_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_agent_id 
    ON form_mapper_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_form_page_route_id 
    ON form_mapper_sessions(form_page_route_id);
CREATE INDEX IF NOT EXISTS idx_form_mapper_sessions_created_at 
    ON form_mapper_sessions(created_at DESC);


-- ============================================================================
-- TABLE: form_map_results
-- Stores the final mapping results (one or more paths per form)
-- ============================================================================
CREATE TABLE IF NOT EXISTS form_map_results (
    id SERIAL PRIMARY KEY,
    
    -- Links
    form_mapper_session_id INTEGER REFERENCES form_mapper_sessions(id) ON DELETE CASCADE NOT NULL,
    form_page_route_id INTEGER REFERENCES form_page_routes(id) ON DELETE CASCADE NOT NULL,
    
    -- Ownership (denormalized for easier queries)
    network_id INTEGER REFERENCES networks(id) ON DELETE SET NULL,
    company_id INTEGER,
    
    -- Path info (for junction discovery - multiple paths per form)
    path_number INTEGER DEFAULT 1,
    path_junctions JSONB DEFAULT '[]'::jsonb,
    -- Example: [{"field": "Application Type", "value": "enterprise", "selector": "select#appType"}]
    
    -- The main result: generated test steps (like path_1_create_verify_person.json)
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Each step: {
    --   "step_number": 1,
    --   "test_case": "TEST_1_create_form",
    --   "action": "fill",
    --   "selector": "input#name",
    --   "value": "John Doe",
    --   "description": "Fill name field",
    --   "junction": false,
    --   "wait_seconds": 0.5
    -- }
    
    -- Extracted form structure (optional - can be derived from steps)
    form_fields JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {"name": "Person Name", "selector": "input#fullName", "type": "text", "required": true},
    --   {"name": "Application Type", "selector": "select#applicationType", "type": "select", "is_junction": true}
    -- ]
    
    -- Field relationships discovered
    field_relationships JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {"parent": "Application Type", "child": "Company Name", "type": "conditional", "condition": "enterprise"}
    -- ]
    
    -- UI issues detected during mapping
    ui_issues JSONB DEFAULT '[]'::jsonb,
    -- Example: ["Red border on email field", "Overlapping buttons in modal"]
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verification_errors JSONB DEFAULT '[]'::jsonb,
    verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for form_map_results
CREATE INDEX IF NOT EXISTS idx_form_map_results_session_id 
    ON form_map_results(form_mapper_session_id);
CREATE INDEX IF NOT EXISTS idx_form_map_results_form_page_route_id 
    ON form_map_results(form_page_route_id);
CREATE INDEX IF NOT EXISTS idx_form_map_results_network_id 
    ON form_map_results(network_id);
CREATE INDEX IF NOT EXISTS idx_form_map_results_path_number 
    ON form_map_results(form_page_route_id, path_number);


-- ============================================================================
-- TABLE: form_mapper_session_logs
-- Detailed event log for debugging and monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS form_mapper_session_logs (
    id SERIAL PRIMARY KEY,
    
    session_id INTEGER REFERENCES form_mapper_sessions(id) ON DELETE CASCADE NOT NULL,
    
    -- Event info
    event_type VARCHAR(50) NOT NULL,
    -- Types: state_change, task_queued, task_completed, ai_call, 
    --        step_executed, error, alert_detected, dom_changed, ui_issue, junction_found
    
    event_data JSONB DEFAULT '{}'::jsonb,
    -- Contains relevant data for the event type
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for form_mapper_session_logs
CREATE INDEX IF NOT EXISTS idx_form_mapper_session_logs_session_id 
    ON form_mapper_session_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_form_mapper_session_logs_event_type 
    ON form_mapper_session_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_form_mapper_session_logs_created_at 
    ON form_mapper_session_logs(created_at DESC);


-- ============================================================================
-- Add trigger to update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_form_mapper_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for form_mapper_sessions
DROP TRIGGER IF EXISTS trigger_form_mapper_sessions_updated_at ON form_mapper_sessions;
CREATE TRIGGER trigger_form_mapper_sessions_updated_at
    BEFORE UPDATE ON form_mapper_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_form_mapper_updated_at();

-- Trigger for form_map_results
DROP TRIGGER IF EXISTS trigger_form_map_results_updated_at ON form_map_results;
CREATE TRIGGER trigger_form_map_results_updated_at
    BEFORE UPDATE ON form_map_results
    FOR EACH ROW
    EXECUTE FUNCTION update_form_mapper_updated_at();


-- ============================================================================
-- Grant permissions (adjust role name as needed)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON form_mapper_sessions TO your_app_role;
-- GRANT ALL PRIVILEGES ON form_map_results TO your_app_role;
-- GRANT ALL PRIVILEGES ON form_mapper_session_logs TO your_app_role;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_role;
