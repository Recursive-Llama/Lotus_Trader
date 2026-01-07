# Portfolio Tracking Database Design

## Approach: JSONB Column in Existing Table

**User's Request**: Add a JSONB column to `wallet_balance_snapshots` table to store position details at snapshot time.

**Why This Works**:
- Simple - no new table needed
- All snapshot data in one place
- Easy to query and aggregate
- JSONB is efficient for this use case

## Schema Change

### Add JSONB Column

```sql
-- Add positions JSONB column to existing table
ALTER TABLE wallet_balance_snapshots 
ADD COLUMN IF NOT EXISTS positions JSONB DEFAULT '[]'::jsonb;

-- Add GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_snapshots_positions_gin 
ON wallet_balance_snapshots USING GIN (positions);

-- Comment
COMMENT ON COLUMN wallet_balance_snapshots.positions IS 
'Array of position objects at snapshot time: [{ticker, value, current_pnl, realized_pnl, extracted, ...}]';
```

### JSONB Structure

**Option 1: Full Details** (User's suggestion)
```json
[
  {
    "ticker": "SOAR",
    "value": 1234.56,
    "current_pnl": 234.56,
    "realized_pnl": 100.00
  },
  {
    "ticker": "TRAX",
    "value": 567.89,
    "current_pnl": -50.00,
    "realized_pnl": 0.00
  }
]
```

**Option 2: Simplified** (User's alternative suggestion)
```json
[
  {
    "ticker": "SOAR",
    "value": 1234.56,
    "extracted": 100.00
  },
  {
    "ticker": "TRAX",
    "value": 567.89,
    "extracted": 0.00
  }
]
```

**Option 3: Full Details with More Context** (Recommended)
```json
[
  {
    "ticker": "SOAR",
    "contract": "9359LVZJ...",
    "chain": "solana",
    "timeframe": "15m",
    "value": 1234.56,
    "current_pnl": 234.56,
    "realized_pnl": 100.00,
    "extracted": 100.00,
    "allocated": 1000.00
  }
]
```

## Code Changes

### Update `balance_snapshot.py`

**Current Code** (lines 35-47):
```python
# 2. Get active positions value
position_rows = (
    self.sb.table("lowcap_positions")
    .select("current_usd_value")
    .eq("status", "active")
    .execute()
).data or []
```

**Updated Code**:
```python
# 2. Get active positions with full details
position_rows = (
    self.sb.table("lowcap_positions")
    .select("token_ticker,token_contract,token_chain,timeframe,current_usd_value,total_pnl_usd,rpnl_usd,total_extracted_usd,total_allocation_usd")
    .eq("status", "active")
    .execute()
).data or []

# Build positions array for JSONB
positions_array = []
for pos in position_rows:
    positions_array.append({
        "ticker": pos.get("token_ticker", "?"),
        "contract": pos.get("token_contract", ""),
        "chain": pos.get("token_chain", ""),
        "timeframe": pos.get("timeframe", ""),
        "value": float(pos.get("current_usd_value", 0) or 0),
        "current_pnl": float(pos.get("total_pnl_usd", 0) or 0),
        "realized_pnl": float(pos.get("rpnl_usd", 0) or 0),
        "extracted": float(pos.get("total_extracted_usd", 0) or 0),
        "allocated": float(pos.get("total_allocation_usd", 0) or 0)
    })

active_positions_value = sum(
    float(row.get("current_usd_value", 0) or 0) 
    for row in position_rows
)
active_positions_count = len(position_rows)
```

**Update Snapshot Insert** (line 53):
```python
snapshot = {
    "snapshot_type": snapshot_type,
    "total_balance_usd": total_balance,
    "usdc_total": usdc_total,
    "active_positions_value": active_positions_value,
    "active_positions_count": active_positions_count,
    "positions": positions_array,  # ← Add this
    "captured_at": datetime.now(timezone.utc).isoformat()
}
```

## Query Examples

### Get All Positions at a Snapshot
```sql
SELECT 
    captured_at,
    positions
FROM wallet_balance_snapshots
WHERE id = 123;
```

### Find Snapshots with Specific Ticker
```sql
SELECT 
    captured_at,
    snapshot_type,
    total_balance_usd
FROM wallet_balance_snapshots
WHERE positions @> '[{"ticker": "SOAR"}]'::jsonb
ORDER BY captured_at DESC;
```

### Get Position Value Over Time
```sql
SELECT 
    captured_at,
    pos->>'ticker' as ticker,
    (pos->>'value')::float as value,
    (pos->>'current_pnl')::float as current_pnl
FROM wallet_balance_snapshots,
     jsonb_array_elements(positions) as pos
WHERE pos->>'ticker' = 'SOAR'
ORDER BY captured_at;
```

### Aggregate Position Values Across Snapshots
```sql
SELECT 
    pos->>'ticker' as ticker,
    AVG((pos->>'value')::float) as avg_value,
    MAX((pos->>'value')::float) as max_value,
    MIN((pos->>'value')::float) as min_value
FROM wallet_balance_snapshots,
     jsonb_array_elements(positions) as pos
WHERE captured_at > NOW() - INTERVAL '7 days'
GROUP BY pos->>'ticker';
```

## Benefits

1. **Simple**: One column, no joins needed
2. **Complete**: All position data at snapshot time
3. **Queryable**: JSONB supports efficient queries
4. **Historical**: Can see position state at any snapshot
5. **Flexible**: Easy to add more fields later

## Considerations

1. **Size**: JSONB can get large with many positions, but typically fine
2. **Indexing**: GIN index makes queries fast
3. **Rollups**: When rolling up snapshots, need to decide how to aggregate positions
   - Option: Keep positions array in rollups (shows state at rollup time)
   - Option: Aggregate position values (lose individual position details)

## Recommendation

Use **Option 3** (Full Details) because:
- Includes ticker, value, current_pnl, realized_pnl, extracted, allocated
- Also includes contract/chain/timeframe for disambiguation
- Easy to calculate derived metrics (unrealized_pnl = current_pnl - realized_pnl)
- Future-proof if we need more fields

## Migration

Since this is adding a column to existing table:
1. Add column with default `'[]'::jsonb`
2. Existing snapshots will have empty array (fine - no historical data)
3. New snapshots will populate positions array
4. No data loss, backward compatible

