Lotus Seer - Two-Service Architecture
Service 1: Scanner (Focus Now)
Batch process that discovers markets, scans, and maintains Top 33 → Top 12 pipeline.

Service 2: Trader (Later)
WebSocket-based service with confirmed parameters:

Subscription: Top 12 only
Max Positions: 6
Scaling Bands: Full (100%) → Half (50%) → Quarter (25%) → Exit
Exit Thresholds: Relative drops (50% clarity, 60% alignment)
Time Exits: Auto-exit when time_remaining < 10% of lifetime
Phase 1: Database Schema
Table: seer_trade_candidates
CREATE TABLE seer_trade_candidates (
    market_id TEXT PRIMARY KEY,
    condition_id TEXT NOT NULL,
    question TEXT,
    category TEXT,
    group_id TEXT,
    
    price_yes FLOAT,
    liquidity FLOAT,
    
    sm_yes_strength FLOAT,
    sm_no_strength FLOAT,
    delta FLOAT,
    
    clarity FLOAT,
    alignment FLOAT,
    trust_factor FLOAT,
    n_eff FLOAT,
    
    priority_1 FLOAT,
    priority_2 FLOAT,
    rank INT,
    tier TEXT,  -- 'top12' or 'top33'
    
    side_recommendation TEXT,
    scanned_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
Table: seer_position_map
CREATE TABLE seer_position_map (
    id SERIAL PRIMARY KEY,
    market_id TEXT NOT NULL,
    wallet_id TEXT NOT NULL,
    
    side TEXT,
    size FLOAT,
    notional FLOAT,
    avg_entry_price FLOAT,
    skill FLOAT,
    weight FLOAT,
    
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(market_id, wallet_id)
);
CREATE INDEX idx_position_map_market ON seer_position_map(market_id);
Table: seer_scan_history
Track which markets were scanned to enable cycling.

CREATE TABLE seer_scan_history (
    market_id TEXT PRIMARY KEY,
    last_scanned_at TIMESTAMP DEFAULT NOW(),
    scan_count INT DEFAULT 1
);
Phase 2: Service 1 Logic
2.1 Market Cycling
Problem: Don't re-scan same 69 markets every cycle.

Solution: Track scanned markets, prioritize unscanned or stale.

async def discover_markets(self, limit=69, max_scan=1000):
    # Get recently scanned market IDs
    recently_scanned = await self.db.fetch("""
        SELECT market_id FROM seer_scan_history 
        WHERE last_scanned_at > NOW() - INTERVAL '1 hour'
    """)
    recently_scanned_ids = {r['market_id'] for r in recently_scanned}
    
    candidates = []
    offset = 0
    
    while len(candidates) < limit and offset < max_scan:
        markets = await self.client.get_markets(limit=100, offset=offset)
        
        for market in markets:
            market_id = market.get('conditionId')
            
            # Prioritize unscanned markets
            if market_id in recently_scanned_ids:
                continue  # Skip recently scanned
            
            if self.is_eligible(market):
                candidates.append(market)
                if len(candidates) >= limit:
                    break
        
        offset += len(markets)
    
    # Record scan
    for c in candidates:
        await self.db.execute("""
            INSERT INTO seer_scan_history (market_id, last_scanned_at, scan_count)
            VALUES ($1, NOW(), 1)
            ON CONFLICT (market_id) DO UPDATE 
            SET last_scanned_at = NOW(), scan_count = scan_count + 1
        """, c.market_id)
    
    return candidates
2.2 Continuous Top 33 → Top 12 Monitoring
Logic:

Each scan produces 69 new candidates.
Level 1 scan → merge with existing Top 33 → re-rank → take new Top 33.
Level 2 scan on Top 33 → produce Top 12.
Persist Top 12 with wallet maps.
async def run_selection_cycle(self):
    # Step 1: Discover NEW markets (cycling)
    new_candidates = await self.discover_markets(limit=69)
    
    # Step 2: Load existing Top 33 from DB
    existing_top33 = await self.load_top33_from_db()
    
    # Step 3: Level 1 scan on new candidates
    for c in new_candidates:
        await self.level1_scan(c)
    
    # Step 4: Merge and re-rank
    all_candidates = existing_top33 + new_candidates
    all_candidates.sort(key=lambda c: c.metrics.priority_1, reverse=True)
    new_top33 = all_candidates[:33]
    
    # Step 5: Level 2 scan on Top 33
    for c in new_top33:
        await self.level2_deep_dive(c)
    
    # Step 6: Rank and select Top 12
    new_top33.sort(key=lambda c: c.metrics.priority_2, reverse=True)
    new_top12 = new_top33[:12]
    
    # Step 7: Persist
    await self.persist_candidates(new_top33, tier='top33')
    await self.persist_candidates(new_top12, tier='top12')
    await self.persist_wallet_maps(new_top12)
2.3 Persist Wallet Maps
After Level 2 scan, we have wallet-by-wallet data. Persist it.

async def persist_wallet_maps(self, candidates):
    for c in candidates:
        # Clear old entries for this market
        await self.db.execute(
            "DELETE FROM seer_position_map WHERE market_id = $1",
            c.market_id
        )
        
        # Insert current wallet positions
        for wallet in c.wallet_positions:
            await self.db.execute("""
                INSERT INTO seer_position_map 
                (market_id, wallet_id, side, size, notional, 
                 avg_entry_price, skill, weight)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, c.market_id, wallet['wallet_id'], wallet['side'],
                wallet['size'], wallet['notional'], 
                wallet['avg_entry_price'], wallet['skill'], wallet['weight'])
Phase 3: Expose Wallet Data from Level 2
Currently, 
level2_deep_dive
 calculates wallet data but doesn't expose it.

Change: Store wallet list in 
MarketCandidate
.

@dataclass
class MarketCandidate:
    # ... existing fields ...
    wallet_positions: List[Dict] = field(default_factory=list)  # NEW
In 
level2_deep_dive
:

# After building wallets list
candidate.wallet_positions = wallets  # Persist for later
