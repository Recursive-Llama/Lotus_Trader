Service 2: Trader Implementation Plan (v2)
Architecture Overview
max_cap
confidence 0.1-1.0
target_notional
thesis broke
Service 1: ScannerContinuous, batch
seer_trade_candidates
PRIORITYRanking + Max Cap
WebSocket Feed
LIVE CONFIDENCEReal-time sizing
Position Sizing
Order Executor
Emergency Exits
⭐ Core Principle: Separation of Concerns
Layer	Source	Speed	Controls
Priority	Service 1 (batch)	Minutes	Entry gating, rotation, max cap
Live Confidence	WebSocket (real-time)	Ticks	Current size (smooth 10-100% of cap)
Emergency Exits	WebSocket (real-time)	Ticks	Thesis-break overrides (rare)
IMPORTANT

Priority is NOT used for exits or scaling. It's slow/batch. Real-time metrics drive sizing.

Phase 1: Priority → Entry & Max Cap
Entry Rules (Priority-gated)
Portfolio Size	Entry Requirement
0 (empty)	Only enter #1 P2
1-2	New must be #1
3-5	New must be top 3
6 (full)	Replace weakest if new is top 3
Max Cap per Market (rank-weighted)
def rank_weight(rank: int) -> float:
    """Higher priority → bigger max cap."""
    weights = {
        1: 1.00, 2: 0.95, 3: 0.90, 4: 0.85,
        5: 0.80, 6: 0.75, 7: 0.60, 8: 0.50,
        9: 0.40, 10: 0.35, 11: 0.30, 12: 0.25
    }
    return weights.get(rank, 0.20)
max_notional = base_position_size * rank_weight(rank)
Example (base = 5% of portfolio = $50 on $1000 portfolio):

Rank 1 → max $50
Rank 3 → max $45
Rank 6 → max $37.50
Rank 12 → max $12.50
Phase 2: Live Confidence → Smooth Scaling
Peak Bootstrapping
IMPORTANT

Initialize peaks from EntrySnapshot to avoid unstable early ratios.

def on_entry(self, market_id, snapshot):
    self.positions[market_id].peaks = {
        'clarity': snapshot.clarity,
        'alignment': snapshot.alignment,
        'delta': abs(snapshot.delta),
        'n_eff': snapshot.n_eff
    }
Confidence Formula
All ratios are current / peak (capped at 1.0):

def compute_confidence(current: dict, peaks: dict) -> float:
    """Smooth confidence score from live SM metrics."""
    clarity_ratio = min(1.0, current['clarity'] / peaks['clarity']) if peaks['clarity'] > 0 else 1.0
    align_ratio = min(1.0, current['alignment'] / peaks['alignment']) if peaks['alignment'] > 0 else 1.0
    delta_ratio = min(1.0, abs(current['delta']) / peaks['delta']) if peaks['delta'] > 0 else 1.0
    neff_ratio = min(1.0, current['n_eff'] / peaks['n_eff']) if peaks['n_eff'] > 0 else 1.0
    
    # Weighted blend
    conf = (
        0.35 * clarity_ratio +
        0.35 * align_ratio +
        0.20 * delta_ratio +
        0.10 * neff_ratio
    )
    
    # Clamp to [0.1, 1.0] - never go below 10% until emergency exit
    return max(0.10, min(1.0, conf))
Position Sizing
target_notional = max_notional * confidence
# Only trade if delta exceeds min order size
delta_from_current = target_notional - current_notional
if abs(delta_from_current) > min_order_size:
    execute_order(delta_from_current)
Smooth Behavior
Confidence	Size (if max=$50)
1.00	$50
0.90	$45
0.80	$40
0.70	$35
0.60	$30
0.50	$25
0.40	$20
0.30	$15
0.20	$10
0.10	$5 (floor until emergency)
No cliff edges. Confidence can go UP or DOWN smoothly.

Phase 3: Emergency Exits (Rare)
CAUTION

Emergency exits are for thesis-break situations only. Most position changes happen via scaling.

Emergency Conditions
def check_emergency_exit(pos, current, time_remaining_ratio) -> Optional[str]:
    """Returns exit reason or None."""
    
    # 1. Delta Sign Flip (with deadzone)
    DEADZONE = 0.02
    current_sign = 1 if current['delta'] > DEADZONE else (-1 if current['delta'] < -DEADZONE else 0)
    if current_sign != 0 and current_sign != pos.entry_delta_sign:
        return f"DELTA_FLIP: SM reversed from {pos.entry_delta_sign} to {current_sign}"
    
    # 2. Trust Collapse (n_eff AND clarity both nuked)
    neff_ratio = current['n_eff'] / pos.peak_n_eff if pos.peak_n_eff > 0 else 1.0
    clarity_ratio = current['clarity'] / pos.peak_clarity if pos.peak_clarity > 0 else 1.0
    if neff_ratio < 0.40 and clarity_ratio < 0.40:
        return f"TRUST_COLLAPSE: n_eff={neff_ratio:.0%}, clarity={clarity_ratio:.0%}"
    
    # 3. Time Pressure (endgame weirdness)
    if time_remaining_ratio < 0.05:
        return f"TIME_EXIT: Only {time_remaining_ratio:.1%} remaining"
    
    # 4. Sustained Rank Collapse (optional, needs state tracking)
    # If rank > 8 for > 30 minutes, market has moved on
    
    return None  # No emergency
Phase 4: Main Loop
async def run_cycle(self):
    """Main trader cycle."""
    
    for market_id, pos in list(self.positions.items()):
        current = await self.get_current_metrics(market_id)
        time_ratio = self.compute_time_remaining(market_id)
        
        # 1. Check emergency exits FIRST
        emergency = self.check_emergency_exit(pos, current, time_ratio)
        if emergency:
            logger.warning(f"EMERGENCY EXIT {market_id}: {emergency}")
            await self.execute_full_exit(market_id)
            continue
        
        # 2. Update peaks (for relative comparisons)
        pos.peak_clarity = max(pos.peak_clarity, current['clarity'])
        pos.peak_alignment = max(pos.peak_alignment, current['alignment'])
        pos.peak_delta = max(pos.peak_delta, abs(current['delta']))
        pos.peak_n_eff = max(pos.peak_n_eff, current['n_eff'])
        
        # 3. Compute confidence and target size
        confidence = self.compute_confidence(current, pos.peaks)
        max_cap = self.base_size * self.rank_weight(current['rank'])
        target = max_cap * confidence
        
        # 4. Scale position smoothly
        await self.scale_to_target(pos, target)
    
    # 5. Check for new entries
    await self.check_entries()
Phase 5: Database Schema Additions
-- Portfolio tracking with peak metrics
CREATE TABLE IF NOT EXISTS seer_portfolio (
    id SERIAL PRIMARY KEY,
    market_id TEXT NOT NULL UNIQUE,
    condition_id TEXT NOT NULL,
    question TEXT,
    
    -- Position
    side TEXT NOT NULL,
    size FLOAT NOT NULL,
    avg_entry_price FLOAT,
    current_notional FLOAT,
    
    -- Entry snapshot
    entry_delta FLOAT,
    entry_delta_sign INT,
    entry_rank INT,
    
    -- Peak metrics (for relative confidence)
    peak_clarity FLOAT,
    peak_alignment FLOAT,
    peak_delta FLOAT,
    peak_n_eff FLOAT,
    
    entered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
Phase 6: Subscription Management
Service 1 writes a version flag when Top 12 changes:

# After persist_trade_candidates():
await self.db.execute("""
    INSERT INTO seer_config (key, value) VALUES ('top12_version', $1)
    ON CONFLICT (key) DO UPDATE SET value = $1
""", str(uuid.uuid4()))
Service 2 checks lazily (every 3 min or after each cycle):

async def check_subscription_updates(self):
    row = await self.db.fetchrow("SELECT value FROM seer_config WHERE key = 'top12_version'")
    if row and row['value'] != self.last_version:
        self.last_version = row['value']
        await self.resubscribe_to_top12()
⚙️ Configuration
@dataclass
class TraderConfig:
    # Position sizing
    base_position_pct: float = 0.05   # 5% of portfolio per rank-1 full-confidence position
    min_order_size: float = 5.0       # Minimum notional change to justify a trade
    
    # Entry (Priority-gated)
    entry_rank_empty: int = 1
    entry_rank_sparse: int = 1
    entry_rank_normal: int = 3
    max_positions: int = 6
    
    # Confidence weights
    clarity_weight: float = 0.35
    alignment_weight: float = 0.35
    delta_weight: float = 0.20
    neff_weight: float = 0.10
    confidence_floor: float = 0.10
    
    # Emergency exit thresholds
    delta_deadzone: float = 0.02
    trust_collapse_neff: float = 0.40
    trust_collapse_clarity: float = 0.40
    time_exit_threshold: float = 0.05