-- Migration: add trade_id tracking for positions and strands

-- lowcap_positions: add current_trade_id for active trade cycles
ALTER TABLE lowcap_positions
    ADD COLUMN IF NOT EXISTS current_trade_id UUID;

CREATE INDEX IF NOT EXISTS idx_lowcap_positions_current_trade_id
    ON lowcap_positions(current_trade_id);

-- ad_strands: add trade_id to link pm_action strands with position_closed strands
ALTER TABLE ad_strands
    ADD COLUMN IF NOT EXISTS trade_id UUID;

CREATE INDEX IF NOT EXISTS idx_ad_strands_trade_id
    ON ad_strands(trade_id);

