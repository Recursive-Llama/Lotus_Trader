# Database Reorganization Summary

## ✅ Completed

### 1. Token Registry Extracted
- **File**: `token_registry_backup.json`
- **Tokens**: 72 unique tokens extracted
- **Data**: `token_id`, `chain_id`, `contract_address`
- **Status**: ✅ Saved and ready for re-seeding

### 2. Old Schemas Archived
- **Location**: `src/database/archive/`
- **Archived Files**:
  - `lowcap_positions_schema.sql` (old schema)
  - `lowcap_positions_simple.sql` (old simple schema)
  - `migration_2025_10_17_positions_pm_columns.sql` (old migration)

### 3. New Schemas Created
- **Location**: `src/database/`
- **New Files**:
  - `lowcap_positions_v4_schema.sql` - Main positions table with multi-timeframe support
  - `position_signals_schema.sql` - Optional time-series history table

## 📋 Next Steps (For You)

### Step 1: Review New Schemas
Review the new schema files:
- `src/database/lowcap_positions_v4_schema.sql`
- `src/database/position_signals_schema.sql`

### Step 2: Delete Old Tables (via SQL Editor)
Once you're ready, delete the old tables:
```sql
-- Drop old tables (in this order due to foreign keys)
DROP TABLE IF EXISTS position_signals CASCADE;
DROP TABLE IF EXISTS lowcap_positions CASCADE;
-- Drop any other related tables you want to clean up
```

### Step 3: Create New Tables (via SQL Editor)
Run the new schema files:
1. `src/database/lowcap_positions_v4_schema.sql`
2. `src/database/position_signals_schema.sql` (optional, but recommended)

### Step 4: Re-seed Token Registry
After tables are created, we'll create a script to re-seed the token registry from `token_registry_backup.json`.

## 🔑 Key Changes in New Schema

### `lowcap_positions` Table
- ✅ Added `timeframe` column (enum: 1m, 15m, 1h, 4h)
- ✅ Added `status` enum (dormant, watchlist, active, paused, archived)
- ✅ Added `bars_count` and `bars_threshold` for data gating
- ✅ Added `alloc_cap_usd` (timeframe-specific allocation)
- ✅ Added `alloc_policy` JSONB (timeframe-specific config)
- ✅ Unique constraint: `(token_contract, token_chain, timeframe)`
- ✅ Changed primary key to UUID (was TEXT before)
- ✅ All existing tracking columns preserved

### `position_signals` Table (New)
- Time-series history of engine outputs
- Links to position via `position_id`
- Stores full JSONB payload from engine
- Optional but recommended for audit/learning

## 📝 Notes

- Token registry is safely backed up in `token_registry_backup.json`
- Old schemas are archived (not deleted) for reference
- New schemas are ready to deploy
- After you delete/create tables, we'll create a re-seeding script

