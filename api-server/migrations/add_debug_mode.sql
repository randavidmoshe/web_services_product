-- add_debug_mode.sql
-- Add debug_mode column to companies table
-- Location: web_services_product/api-server/migrations/add_debug_mode.sql
--
-- Run with: psql -U postgres -d formfinder -f add_debug_mode.sql

ALTER TABLE companies 
ADD COLUMN IF NOT EXISTS debug_mode BOOLEAN DEFAULT FALSE;

-- Verify
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'companies' AND column_name = 'debug_mode';
