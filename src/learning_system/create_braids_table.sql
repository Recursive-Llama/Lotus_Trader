-- Create ad_braids table for storing braid data
CREATE TABLE IF NOT EXISTS public.ad_braids (
    id TEXT PRIMARY KEY,
    level INTEGER NOT NULL DEFAULT 1,
    strand_type TEXT NOT NULL,
    strand_ids TEXT[] NOT NULL,
    resonance_score FLOAT NOT NULL,
    cluster_size INTEGER NOT NULL,
    cluster_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on strand_type for faster queries
CREATE INDEX IF NOT EXISTS idx_ad_braids_strand_type ON public.ad_braids(strand_type);

-- Create index on level for faster queries
CREATE INDEX IF NOT EXISTS idx_ad_braids_level ON public.ad_braids(level);

-- Create index on resonance_score for faster queries
CREATE INDEX IF NOT EXISTS idx_ad_braids_resonance_score ON public.ad_braids(resonance_score);

-- Create index on created_at for faster queries
CREATE INDEX IF NOT EXISTS idx_ad_braids_created_at ON public.ad_braids(created_at);

-- Add RLS (Row Level Security) if needed
-- ALTER TABLE public.ad_braids ENABLE ROW LEVEL SECURITY;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON public.ad_braids TO authenticated;
-- GRANT ALL ON public.ad_braids TO service_role;
