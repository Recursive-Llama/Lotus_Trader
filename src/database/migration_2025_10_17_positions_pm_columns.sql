-- Migration: Add PM columns to lowcap_positions
-- Date: 2025-10-17

-- Add JSONB features cache for PM inputs/diagnostics
ALTER TABLE IF EXISTS public.lowcap_positions
  ADD COLUMN IF NOT EXISTS features JSONB;

-- Add PM state/control fields
ALTER TABLE IF EXISTS public.lowcap_positions
  ADD COLUMN IF NOT EXISTS cooldown_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_review_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS time_patience_h INT,
  ADD COLUMN IF NOT EXISTS reentry_lock_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS trend_entry_count INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS new_token_mode BOOLEAN DEFAULT FALSE;

-- Optional helpful index for JSONB queries on features
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_features_gin
  ON public.lowcap_positions USING GIN (features);

-- Optional: quick access on review time
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_last_review
  ON public.lowcap_positions (last_review_at DESC);


