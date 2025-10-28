-- Migration: Add missing columns to portfolio_bands table
-- Date: 2025-10-21
-- Purpose: Fix bands_calc job by adding core_pressure and delta_core columns

-- Add core_pressure column (float, nullable)
ALTER TABLE portfolio_bands 
ADD COLUMN IF NOT EXISTS core_pressure FLOAT;

-- Add delta_core column (float, nullable) 
ALTER TABLE portfolio_bands 
ADD COLUMN IF NOT EXISTS delta_core FLOAT;

-- Add comments for documentation
COMMENT ON COLUMN portfolio_bands.core_pressure IS 'Core count pressure component (0-1) calculated from core_count vs ideal_core';
COMMENT ON COLUMN portfolio_bands.delta_core IS 'Core count delta for portfolio breathing adjustments';

-- Update existing records to have default values
UPDATE portfolio_bands 
SET 
    core_pressure = 0.0,
    delta_core = 0.0
WHERE core_pressure IS NULL OR delta_core IS NULL;

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'portfolio_bands' 
    AND column_name IN ('core_pressure', 'delta_core')
ORDER BY column_name;
