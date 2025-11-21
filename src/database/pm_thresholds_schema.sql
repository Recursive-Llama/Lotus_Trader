-- PM Thresholds Schema
-- Stores tunable thresholds for Portfolio Manager and Uptrend Engine
-- Allows live updates and future auto-tuning

CREATE TABLE IF NOT EXISTS public.pm_thresholds (
    key TEXT NOT NULL,                    -- Threshold key (e.g., 'ts_score_aggressive', 'ox_score_normal', 'trim_size_e_high')
    value JSONB NOT NULL,                 -- Threshold value (can be float, object, array, etc.)
    timeframe TEXT DEFAULT '',            -- Timeframe this applies to (1m, 15m, 1h, 4h, '' = all timeframes)
    phase TEXT DEFAULT '',                -- Phase this applies to (dip, recover, euphoria, etc., '' = all phases)
    a_level TEXT DEFAULT '',              -- A/E level this applies to (aggressive, normal, patient, '' = all levels)
    min_version INTEGER,                  -- Minimum system version required (for gradual rollouts)
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,                      -- Source of update ('system', 'manual', 'learning_system')
    notes TEXT,                           -- Additional notes or description
    PRIMARY KEY (key, timeframe, phase, a_level)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_pm_thresholds_key ON public.pm_thresholds(key);
CREATE INDEX IF NOT EXISTS idx_pm_thresholds_timeframe ON public.pm_thresholds(timeframe);
CREATE INDEX IF NOT EXISTS idx_pm_thresholds_phase ON public.pm_thresholds(phase);
CREATE INDEX IF NOT EXISTS idx_pm_thresholds_a_level ON public.pm_thresholds(a_level);
CREATE INDEX IF NOT EXISTS idx_pm_thresholds_updated_at ON public.pm_thresholds(updated_at DESC);

-- Comments
COMMENT ON TABLE public.pm_thresholds IS 'Stores tunable thresholds for Portfolio Manager and Uptrend Engine. Allows live updates and future auto-tuning.';
COMMENT ON COLUMN public.pm_thresholds.key IS 'Threshold key identifier (e.g., ts_score_aggressive, ox_score_normal, trim_size_e_high)';
COMMENT ON COLUMN public.pm_thresholds.value IS 'Threshold value (JSONB - can be float, object, array, etc.)';
COMMENT ON COLUMN public.pm_thresholds.timeframe IS 'Timeframe this threshold applies to (1m, 15m, 1h, 4h, empty string = all timeframes)';
COMMENT ON COLUMN public.pm_thresholds.phase IS 'Phase this threshold applies to (dip, recover, euphoria, etc., empty string = all phases)';
COMMENT ON COLUMN public.pm_thresholds.a_level IS 'A/E level this threshold applies to (aggressive, normal, patient, empty string = all levels)';
COMMENT ON COLUMN public.pm_thresholds.min_version IS 'Minimum system version required (for gradual rollouts)';
COMMENT ON COLUMN public.pm_thresholds.updated_at IS 'Timestamp of last update';
COMMENT ON COLUMN public.pm_thresholds.updated_by IS 'Source of update (system, manual, learning_system)';
COMMENT ON COLUMN public.pm_thresholds.notes IS 'Additional notes or description';

-- Example threshold keys (for reference):
-- 'ts_score_aggressive' - TS score threshold for aggressive A level
-- 'ts_score_normal' - TS score threshold for normal A level
-- 'ts_score_patient' - TS score threshold for patient A level
-- 'dx_score_aggressive' - DX score threshold for aggressive A level
-- 'ox_score_aggressive' - OX score threshold for aggressive E level
-- 'trim_size_e_high' - Trim size for E >= 0.7
-- 'trim_size_e_medium' - Trim size for E >= 0.3
-- 'trim_size_e_low' - Trim size for E < 0.3
-- 'entry_size_s1_aggressive' - Entry size for S1 with aggressive A
-- 'entry_size_s2_aggressive' - Entry size for S2 with aggressive A

