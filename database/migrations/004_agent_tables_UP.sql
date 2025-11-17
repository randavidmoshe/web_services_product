-- Migration 004: Add Agent Tables
-- UP migration - Creates tables
-- Location: web_services_product/database/migrations/004_agent_tables_UP.sql

-- ========== AGENTS TABLE ==========
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Agent info
    hostname VARCHAR(255),
    platform VARCHAR(50),
    version VARCHAR(20),
    
    -- Status
    status VARCHAR(20) DEFAULT 'offline',
    last_heartbeat TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_agents_agent_id ON agents(agent_id);
CREATE INDEX idx_agents_company_id ON agents(company_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_last_heartbeat ON agents(last_heartbeat);

-- ========== AGENT TASKS TABLE ==========
CREATE TABLE IF NOT EXISTS agent_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- Ownership
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(100) REFERENCES agents(agent_id) ON DELETE SET NULL,
    
    -- Task details
    task_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    
    -- Results
    result JSONB,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_agent_tasks_task_id ON agent_tasks(task_id);
CREATE INDEX idx_agent_tasks_company_id ON agent_tasks(company_id);
CREATE INDEX idx_agent_tasks_user_id ON agent_tasks(user_id);
CREATE INDEX idx_agent_tasks_agent_id ON agent_tasks(agent_id);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX idx_agent_tasks_created_at ON agent_tasks(created_at);

-- Comments
COMMENT ON TABLE agents IS 'Agents running on customer networks';
COMMENT ON TABLE agent_tasks IS 'Tasks queued for agents to execute';
