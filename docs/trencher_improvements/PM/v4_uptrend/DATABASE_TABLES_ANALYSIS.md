# Database Tables Analysis - What We Need

## ✅ Tables We NEED (Keep & Verify Schemas)

### 1. Position Tables
- **`lowcap_positions`** ✅
  - **Status**: Creating v4 schema with multi-timeframe support
  - **Used by**: Engine, PM, Trader, Decision Maker
  - **Schema**: `src/database/lowcap_positions_v4_schema.sql`

### 2. Price Data Tables
- **`lowcap_price_data_ohlc`** ✅
  - **Status**: ✅ Schema restored (already has `timeframe` column support)
  - **Used by**: Engine (reads OHLC bars per timeframe)
  - **Key**: Has `timeframe` column (1m, 5m, 15m, 1h, 4h, 1d)
  - **Location**: `src/database/lowcap_price_data_ohlc_schema.sql`

- **`lowcap_price_data_1m`** ✅
  - **Status**: ✅ Schema created
  - **Used by**: Price collector (writes 1m price points), OHLC rollup (reads to create OHLC)
  - **Purpose**: Raw 1m price data that gets rolled up to OHLC bars
  - **Location**: `src/database/lowcap_price_data_1m_schema.sql`

### 3. Strand Tables (Learning System)
- **`ad_strands`** ✅ **ONLY STRANDS TABLE** (lowercase)
  - **Status**: ✅ Schema restored
  - **Used by**: Learning System, Social Ingest, Decision Maker, PM Core Tick
  - **Note**: All strand types use this single table with different `kind` values:
    - `kind='social_lowcap'` - Social Ingest strands
    - `kind='decision_lowcap'` - Decision Maker strands
    - `kind='pm_action'` - PM Core Tick strands
    - `kind='pattern'` - RDI patterns
    - `kind='prediction_review'` - CIL predictions
    - `kind='trading_decision'` - Decision Maker decisions
    - `kind='execution_outcome'` - Trader execution outcomes
  - **✅ Confirmed**: PM Core Tick writes to `ad_strands` table with `kind='pm_action'`
  - **Location**: `src/database/ad_strands_schema.sql`

### 4. Portfolio/Phase Tables (A/E Scores)
- **`portfolio_bands`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: PM Core Tick (reads `cut_pressure` - line 62)
  - **Purpose**: Portfolio-level metrics (cut_pressure, dominance, phase)
  - **Location**: `src/database/portfolio_bands_schema.sql`

- **`phase_state`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: PM Core Tick (reads `phase` - line 50)
  - **Purpose**: Phase tracking (macro, meso, micro)
  - **Location**: `src/database/phase_state_schema.sql`

### 5. Other Essential Tables
- **`curators`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: Social Ingest, Decision Maker (curator scoring)
  - **Location**: `src/database/curators_schema.sql`

- **`position_signals`** ✅
  - **Status**: Creating new schema
  - **Used by**: Engine (writes time-series history), Learning System (reads for analysis)
  - **Schema**: `src/database/position_signals_schema.sql`

## ❓ Tables to Verify (May or May Not Need)

### Majors Data (A/E Macro/Meso/Micro Scores)
- **`majors_price_data_ohlc`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: A/E score calculations (macro, meso, micro phases)
  - **Purpose**: OHLCV data for major cryptocurrencies (BTC, ETH, etc.)
  - **Note**: NOT for dominance (dominance is CoinGecko API)
  - **Location**: `src/database/majors_price_data_ohlc_schema.sql`

- **`majors_trades_ticks`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: Rollup to create majors OHLCV data
  - **Purpose**: Raw trade ticks from Hyperliquid, rolled up to 1m OHLCV
  - **Location**: `src/database/majors_trades_ticks_schema.sql`

### Balance/Wallet Tracking
- **`wallet_balances`** ✅
  - **Status**: ✅ Schema restored
  - **Used by**: Executor (balance checks before trades)
  - **Purpose**: Track native token balances per chain
  - **Location**: `src/database/wallet_balances_schema.sql`

### Generic Price Data
- **`price_data_schema`** ❓
  - **Status**: Archived
  - **Question**: Is this a generic price table or specific to something?
  - **Location**: `src/database/archive/price_data_schema.sql`

## ❌ Tables We DON'T Need (Can Delete)

### Old/Deprecated Systems
- **`curators_positions`** ❌ - Old curator positions system
- **`curators_positions_schema_v2`** ❌ - Old curator positions v2
- **`uptrend_state_events`** ❌ - Old event system (we use direct calls now)
- **`pm_action_queue`** ❌ - Old PM queue (we use direct calls now)

### Separate Systems (Not Part of Lowcap PM)
- **`alpha_detector`** ❌ - Separate alpha detection system
- **`alpha_market_data`** ❌ - Separate alpha market data
- **`agent_capabilities`** ❌ - Separate agent system

### Views (Not Tables)
- **`resonance_views`** ❌ - Views, not tables

## 📋 Action Items

### 1. Verify Required Tables
- [x] ✅ `ad_strands` - Single strands table (lowercase) - Schema exists
- [ ] Check if `lowcap_price_data_1m` schema exists or needs creation
- [ ] Verify if majors tables are needed for dominance calculations

### 2. Create Missing Schemas
- [ ] `lowcap_price_data_ohlc` - Update with `timeframe` column support
- [ ] `lowcap_price_data_1m` - Create if doesn't exist
- [x] ✅ `ad_strands` - Single strands table (lowercase) - Schema exists
- [ ] `portfolio_bands` - Restore from archive
- [ ] `phase_state` - Restore from archive
- [ ] `curators` - Restore from archive

### 3. Verify Optional Tables
- [ ] Check if majors tables needed for dominance
- [ ] Check if wallet_balances needed
- [ ] Check if price_data (generic) needed

## 🔍 Questions to Answer

1. ✅ **Is `ad_strands` the only strands table?** - **ANSWERED: YES**
   - All strand types (social_lowcap, decision_lowcap, pm_action, pattern, etc.) use `ad_strands` with different `kind` values
   - Table name is lowercase: `ad_strands`

2. **Are majors tables needed for dominance calculations?**
   - Check: Does `portfolio_bands` read from majors tables for BTC.d/USDT.d?

4. **Is `lowcap_price_data_1m` a separate table or part of `lowcap_price_data_ohlc`?**
   - Check: How does price collector store 1m data?

5. **Do we need `wallet_balances` for balance tracking?**
   - Check: Does executor check balances before trades?

## ⚠️ Code Updates Required After Schema Change

### Table Name Change: `AD_strands` → `ad_strands` (lowercase)

**Impact**: Several Python files use uppercase `'AD_strands'` in Supabase client calls. These need to be updated to lowercase `'ad_strands'` to match the new schema.

**Files that need updates**:
1. `src/intelligence/universal_learning/systems/centralized_learning_system.py` (4 references)
2. `src/intelligence/universal_learning/pipeline/learning_pipeline.py` (3 references)
3. `src/intelligence/universal_learning/engines/braid_level_manager.py` (4 references)
4. `src/intelligence/universal_learning/pipeline/per_cluster_learning_system.py` (2 references)
5. `src/intelligence/universal_learning/pipeline/multi_cluster_grouping_engine.py` (1 reference)
6. `src/llm_integration/central_intelligence_router.py` (3 references)

**Note**: Most other files already use lowercase `'ad_strands'` (e.g., `pm_core_tick.py`, `supabase_manager.py`), so they should work fine.

**Action**: Update all `.table('AD_strands')` → `.table('ad_strands')` before deploying the new schema.

