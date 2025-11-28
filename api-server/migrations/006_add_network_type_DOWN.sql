-- Migration 006 DOWN: Remove network_type and updated_at from networks table
-- Date: 2025-11-27
-- Description: Rollback - removes network_type column and updated_at timestamp

-- Step 1: Drop the check constraint
ALTER TABLE networks 
DROP CONSTRAINT IF EXISTS networks_network_type_check;

-- Step 2: Drop the columns
ALTER TABLE networks 
DROP COLUMN IF EXISTS network_type,
DROP COLUMN IF EXISTS updated_at;
