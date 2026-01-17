# Scaling A/E v2 - Schema Changes

## Summary

**No changes needed to existing tables** - all new data structures use existing JSONB columns or a new table.

## Changes

### 1. New Table: `token_timeframe_blocks`

**Purpose**: Episode-based token blocking (deterministic risk control)

**Migration**: `src/database/migrations/2025_12_29_add_token_timeframe_blocks.sql`

**Columns**:
- `token_contract`, `token_chain`, `timeframe`, `book_id` (composite PK)
- `blocked_s1`, `blocked_s2` (boolean flags)
- `last_s1_failure_ts`, `last_s2_failure_ts`, `last_success_ts` (timestamps)
- `created_at`, `updated_at` (tracking)

**Usage**: 
- Blocks S1/S2 entry after failed attempts
- Unblocks when successful episode observed
- NOT learned - immediate risk control

### 2. JSONB Structures in `lowcap_positions.features.pm_execution_history`

**No schema change** - uses existing `features` JSONB column.

**New structures added**:

#### `trim_pool` (new)
```json
{
  "usd_basis": 150.0,
  "recovery_started": false,
  "dx_count": 0,
  "dx_last_price": null,
  "dx_next_arm": null
}
```

#### `last_emergency_exit` (new)
```json
{
  "timestamp": "2025-12-29T14:00:00Z",
  "exit_value_usd": 500.0,
  "rebuy_used": false
}
```

#### Existing fields (already in use):
- `last_s1_buy`, `last_s2_buy`, `last_s3_buy`, `last_reclaim_buy`
- `last_trim`
- `last_emergency_exit_ts`
- `prev_state`

## Migration Steps

1. **Run the migration**:
   ```sql
   \i src/database/migrations/2025_12_29_add_token_timeframe_blocks.sql
   ```

2. **Verify**:
   ```sql
   -- Check table exists
   SELECT * FROM token_timeframe_blocks LIMIT 1;
   
   -- Check JSONB structure (should work automatically)
   SELECT features->'pm_execution_history'->'trim_pool' 
   FROM lowcap_positions 
   WHERE features->'pm_execution_history'->'trim_pool' IS NOT NULL 
   LIMIT 1;
   ```

## Backward Compatibility

✅ **Fully backward compatible**:
- `token_timeframe_blocks` is a new table (no impact on existing data)
- JSONB structures are additive (existing `pm_execution_history` fields remain)
- Code handles missing fields gracefully (defaults to empty structures)

## Rollback

If needed, rollback is simple:
```sql
DROP TABLE IF EXISTS token_timeframe_blocks;
-- JSONB structures can remain (they're just unused data)
```

