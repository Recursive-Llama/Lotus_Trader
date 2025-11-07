# Database Schemas Restored/Created Summary

## ✅ Schemas Restored from Archive

### Core Tables
1. **`AD_strands_schema.sql`** (from `memory_strands.sql`)
   - Only strands table - all strand types use this with different `kind` values
   - Used by: Learning System, Social Ingest, Decision Maker, PM Core Tick

2. **`portfolio_bands_schema.sql`**
   - Portfolio-level metrics (cut_pressure, dominance, phase)
   - Used by: PM Core Tick (A/E score calculations)

3. **`phase_state_schema.sql`**
   - Phase tracking (macro, meso, micro)
   - Used by: PM Core Tick (A/E score calculations)

4. **`curators_schema.sql`**
   - Curator management and performance tracking
   - Used by: Social Ingest, Decision Maker

### Price Data Tables
5. **`lowcap_price_data_ohlc_schema.sql`**
   - Multi-timeframe OHLCV data (already has `timeframe` column)
   - Supports: 1m, 5m, 15m, 1h, 4h, 1d
   - Used by: Engine (reads OHLC bars per timeframe)

6. **`majors_price_data_ohlc_schema.sql`**
   - OHLCV data for major cryptocurrencies (BTC, ETH, etc.)
   - Used by: A/E score calculations (macro, meso, micro phases)
   - Note: NOT for dominance (dominance is CoinGecko API)

7. **`majors_trades_ticks_schema.sql`**
   - Raw trade ticks from Hyperliquid
   - Used by: Rollup to create majors OHLCV data

### Other Tables
8. **`wallet_balances_schema.sql`**
   - Native token balance tracking per chain
   - Used by: Executor (balance checks before trades)

## ✅ Schemas Created (New)

1. **`lowcap_price_data_1m_schema.sql`** (NEW)
   - Raw 1-minute price points (not OHLC bars)
   - Used by: Price collector (writes), OHLC rollup (reads to create OHLC)
   - Purpose: Source data for rolling up to OHLC bars for all timeframes

2. **`lowcap_positions_v4_schema.sql`** (NEW - from earlier)
   - Multi-timeframe position model
   - 4 positions per token (1m, 15m, 1h, 4h)
   - Unique constraint: (token_contract, chain, timeframe)

3. **`position_signals_schema.sql`** (NEW - from earlier)
   - Time-series history of engine outputs
   - Optional but recommended for audit/learning

## 📋 All Schemas Ready

All required schemas are now in `src/database/`:
- ✅ `lowcap_positions_v4_schema.sql`
- ✅ `position_signals_schema.sql`
- ✅ `AD_strands_schema.sql`
- ✅ `portfolio_bands_schema.sql`
- ✅ `phase_state_schema.sql`
- ✅ `curators_schema.sql`
- ✅ `lowcap_price_data_ohlc_schema.sql`
- ✅ `lowcap_price_data_1m_schema.sql` (NEW)
- ✅ `majors_price_data_ohlc_schema.sql`
- ✅ `majors_trades_ticks_schema.sql`
- ✅ `wallet_balances_schema.sql`

## ⚠️ Verification Needed

1. **PM Core Tick writes to `ad_strands`** (line 127 in pm_core_tick.py)
   - Question: Is `ad_strands` a view/alias for `AD_strands`?
   - Or should PM be updated to write to `AD_strands` with `kind='pm_action'`?
   - Action: Verify this before creating tables

## 📝 Next Steps

1. Review all schemas in `src/database/`
2. Verify `ad_strands` vs `AD_strands` question
3. Delete old tables via SQL editor
4. Create new tables by running schema files in order:
   - Core tables first (positions, strands)
   - Then price data tables
   - Then supporting tables (portfolio_bands, phase_state, curators, wallet_balances)
5. Re-seed token registry from `token_registry_backup.json`

