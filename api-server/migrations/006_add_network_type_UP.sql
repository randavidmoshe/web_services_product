-- Migration 006: Add network_type and updated_at to networks table
-- Date: 2025-11-27
-- Description: Adds network_type column ("qa", "staging", "production") and updated_at timestamp

-- Step 1: Add the new columns
ALTER TABLE networks 
ADD COLUMN network_type VARCHAR(20),
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

-- Step 2: Update existing rows to have a default network_type (set to 'qa')
-- This is needed because network_type will be NOT NULL
UPDATE networks SET network_type = 'qa' WHERE network_type IS NULL;

-- Step 3: Now make network_type NOT NULL
ALTER TABLE networks ALTER COLUMN network_type SET NOT NULL;

-- Step 4: Add a check constraint to ensure valid values
ALTER TABLE networks 
ADD CONSTRAINT networks_network_type_check 
CHECK (network_type IN ('qa', 'staging', 'production'));
