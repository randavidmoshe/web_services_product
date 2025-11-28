-- Migration 007: Add API Key to Agents table
-- File: 007_add_agent_api_key.sql
-- 
-- This migration adds the api_key column for secure agent authentication.

-- Add api_key column to agents table
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS api_key VARCHAR(64) UNIQUE;

-- Create index for fast API key lookups
CREATE INDEX IF NOT EXISTS idx_agents_api_key ON agents(api_key);
