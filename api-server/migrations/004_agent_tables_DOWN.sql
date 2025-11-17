-- Migration 004: Remove Agent Tables
-- DOWN migration - Rollback (removes tables)
-- Location: web_services_product/database/migrations/004_agent_tables_DOWN.sql

-- Drop tables in reverse order (due to foreign keys)
DROP TABLE IF EXISTS agent_tasks CASCADE;
DROP TABLE IF EXISTS agents CASCADE;

-- Drop indexes (if tables were dropped, indexes are auto-dropped, but explicit is good)
DROP INDEX IF EXISTS idx_agent_tasks_created_at;
DROP INDEX IF EXISTS idx_agent_tasks_status;
DROP INDEX IF EXISTS idx_agent_tasks_agent_id;
DROP INDEX IF EXISTS idx_agent_tasks_user_id;
DROP INDEX IF EXISTS idx_agent_tasks_company_id;
DROP INDEX IF EXISTS idx_agent_tasks_task_id;

DROP INDEX IF EXISTS idx_agents_last_heartbeat;
DROP INDEX IF EXISTS idx_agents_status;
DROP INDEX IF EXISTS idx_agents_company_id;
DROP INDEX IF EXISTS idx_agents_agent_id;
