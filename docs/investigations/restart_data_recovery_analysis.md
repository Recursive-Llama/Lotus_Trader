# Restart & Data Recovery Analysis

**Date**: 2025-12-21  
**Context**: System hit Supabase data allowance limits, investigating restart recovery capabilities

---

## Executive Summary

**Good News**: The system is **well-designed for restarts**. Most data can be regenerated automatically on startup. However, there are some considerations for a fresh start vs. recovery.

**Recommendation**: If you're just starting (few days of data), **a fresh start is likely easier** than trying to recover from a corrupted/incomplete state. The bootstrap system will rebuild everything automatically.

---

## 1. What Happens on Startup/Restart

### Bootstrap Sequence (`bootstrap_system.py`)

The system runs a comprehensive bootstrap on every startup (via `run_trade.py`):

1. **Database Tables Check** - Verifies all required tables exist
2. **Wallet Balances** - Collects initial balances (non-critical if empty)
3. **Price Data Collection** - Verifies majors/lowcaps are collecting
4. **Hyperliquid WS** - Starts WebSocket connection (if enabled)
5. **Regime Driver Positions** - Auto-creates if missing (BTC, ALT, buckets, dominance)
6. **Regime Price Data** - **Backfills majors from Binance** (up to 666 bars per timeframe)
7. **Regime TA Computation** - Computes technical indicators
8. **Regime State Computation** - Runs uptrend engine to compute states

### Key Bootstrap Features

- **Non-fatal failures**: Missing historical data is logged but doesn't stop startup
- **Auto-creation**: Regime driver positions are created automatically if missing
- **Smart backfill**: Only backfills what's needed (checks existing data first)
- **Capped backfill**: Limits to 666 bars per timeframe to avoid excessive data

---

## 2. What Data Gets Backfilled

### Automatic Backfill (On Startup)

**Majors (BTC, SOL, ETH, BNB)**:
- Source: Binance API (free, no auth)
- Timeframes: 1m, 1h, 1d
- Amount: Up to 666 bars per timeframe (capped)
  - 1m: ~11 hours of data
  - 1h: ~28 days of data
  - 1d: ~2 years of data
- When: Only if existing data is insufficient (< 333 bars)

**ALT Composite**:
- Computed from majors (SOL, ETH, BNB, HYPE)
- No external backfill needed - computed from majors data

**Lowcap Tokens**:
- **NOT backfilled on startup** - only collected going forward
- GeckoTerminal backfill happens **on-demand** when rollup needs data

### What Does NOT Get Backfilled

- **Lowcap 1m price points** - Only collected going forward
- **Lowcap OHLC bars** - Only created from ongoing 1m collection
- **Learning system data** (strands, lessons) - Starts fresh
- **Position history** - Starts fresh
- **Social signals** - Starts fresh

---

## 3. Critical vs. Regenerable Data

### 🔴 Critical Data (Must Preserve or Recreate)

**1. Active Positions** (`lowcap_positions` with `status='active'`):
- Current holdings, quantities, entry prices
- **Action**: Export before wipe, or manually recreate
- **Impact**: HIGH - Without this, system doesn't know what it owns

**2. Wallet Balances**:
- Current SOL/USDC balances
- **Action**: Automatically collected on startup (non-critical)
- **Impact**: MEDIUM - System can query wallet directly

**3. Token Registry** (if you have custom tokens):
- Token contracts, chains, symbols
- **Action**: Export before wipe if you have custom entries
- **Impact**: MEDIUM - Most tokens come from social signals anyway

### 🟢 Regenerable Data (Auto-rebuilt on Startup)

**1. Regime Price Data**:
- Majors: Backfilled from Binance (up to 666 bars)
- ALT composite: Computed from majors
- Dominance: Collected going forward (no historical backfill)
- **Time to rebuild**: ~2-5 minutes (depends on backfill amount)

**2. Regime Driver Positions**:
- Auto-created if missing (BTC, ALT, buckets, dominance)
- **Time to rebuild**: Instant (just creates records)

**3. Technical Analysis (TA)**:
- Computed from price data
- **Time to rebuild**: ~1-2 minutes (after price data exists)

**4. Regime States**:
- Computed by uptrend engine from TA data
- **Time to rebuild**: ~1-2 minutes (after TA exists)

**5. Lowcap Price Data**:
- Collected going forward (1m price points)
- OHLC bars created via rollup
- **Time to rebuild**: Builds up over time (no historical backfill)

**6. Learning System Data**:
- Strands, lessons, patterns
- **Time to rebuild**: Builds up over time as system runs

---

## 4. Time to Rebuild

### Startup Bootstrap Timeline

**Fast Path** (if data already exists):
- Database check: < 1 second
- Wallet balances: < 1 second
- Price data check: < 1 second
- Regime positions: < 1 second
- Regime price data: < 1 second (if already exists)
- TA computation: ~30 seconds - 2 minutes
- State computation: ~30 seconds - 2 minutes
- **Total**: ~2-5 minutes

**Full Backfill Path** (if starting fresh):
- Database check: < 1 second
- Wallet balances: < 1 second
- Price data check: < 1 second
- Regime positions: < 1 second
- **Regime price backfill**: ~2-5 minutes (Binance API calls)
- ALT composite: ~10 seconds
- TA computation: ~1-2 minutes
- State computation: ~1-2 minutes
- **Total**: ~5-10 minutes

**Note**: System starts accepting new data immediately, even while backfill is running.

---

## 5. Fresh Start vs. Recovery

### Scenario A: Fresh Start (Wipe Everything)

**Pros**:
- ✅ Clean slate - no corrupted/incomplete data
- ✅ No orphaned records or inconsistencies
- ✅ Bootstrap system handles everything automatically
- ✅ Faster than trying to fix corrupted data

**Cons**:
- ❌ Lose learning system data (strands, lessons, patterns)
- ❌ Lose position history (if you want to keep it)
- ❌ Lose social signal history
- ❌ Need to manually recreate active positions (if any)

**Best For**:
- Early stage (few days/weeks of data)
- When data is corrupted/incomplete
- When you want a clean start

### Scenario B: Recovery (Keep Existing Data)

**Pros**:
- ✅ Preserves learning system data
- ✅ Preserves position history
- ✅ Preserves social signal history
- ✅ No need to recreate active positions

**Cons**:
- ⚠️ May have corrupted/incomplete data
- ⚠️ May have orphaned records
- ⚠️ Bootstrap may skip backfill if it thinks data exists (but data might be incomplete)

**Best For**:
- When you have valuable learning data
- When you have long position history
- When data is mostly intact

---

## 6. Restart Recovery Assessment

### ✅ What Works Well

1. **Automatic Backfill**: System automatically backfills majors from Binance if data is insufficient
2. **Auto-Creation**: Regime driver positions are created automatically
3. **Non-Fatal Failures**: Missing data doesn't stop startup
4. **Smart Detection**: System checks existing data before backfilling

### ⚠️ Potential Issues

1. **Incomplete Data Detection**: 
   - System checks bar count (< 333 bars triggers backfill)
   - But if you have 400 bars that are old/stale, it won't backfill
   - **Solution**: Manual backfill or wipe

2. **Lowcap Data**:
   - No automatic backfill for lowcap tokens
   - Only builds up over time
   - **Solution**: GeckoTerminal backfill happens on-demand when rollup needs it

3. **Learning System**:
   - No automatic recovery of learning data
   - Starts fresh on wipe
   - **Solution**: Export/import if valuable

---

## 7. Recommendations

### If You're Just Starting (Few Days of Data)

**Recommendation**: **Fresh Start (Wipe Everything)**

**Steps**:
1. Export active positions (if any) to a JSON file
2. Wipe all tables (or drop and recreate)
3. Restart system - bootstrap will handle everything
4. Manually recreate active positions (if any)

**Why**:
- You don't have much valuable historical data yet
- Clean slate avoids any corruption issues
- Bootstrap system will rebuild everything automatically
- Faster than trying to fix incomplete data

### If You Have Valuable Data

**Recommendation**: **Selective Recovery**

**Steps**:
1. Export critical data:
   - Active positions
   - Learning system data (if valuable)
   - Token registry (if custom)
2. Wipe price/OHLC tables (regenerable)
3. Keep positions/learning tables
4. Restart - bootstrap will backfill price data

**Why**:
- Preserves valuable learning data
- Regenerates price data automatically
- Best of both worlds

---

## 8. Wipe & Restart Checklist

If you decide to wipe everything:

### Pre-Wipe

- [ ] Export active positions (if any)
- [ ] Export learning system data (if valuable)
- [ ] Export token registry (if custom tokens)
- [ ] Note current wallet balances (for verification)

### Wipe

- [ ] Drop all tables (or truncate)
- [ ] Recreate schemas (run SQL files)
- [ ] Verify tables exist

### Post-Wipe

- [ ] Restart system
- [ ] Verify bootstrap completes successfully
- [ ] Check regime price data is backfilled
- [ ] Verify regime driver positions exist
- [ ] Recreate active positions (if any)
- [ ] Verify wallet balances are collected

---

## 9. Bootstrap System Code Reference

**Key Files**:
- `src/intelligence/lowcap_portfolio_manager/jobs/bootstrap_system.py` - Main bootstrap logic
- `src/intelligence/lowcap_portfolio_manager/jobs/regime_price_collector.py` - Binance backfill
- `src/run_trade.py` - Startup sequence (calls bootstrap)

**Key Functions**:
- `BootstrapSystem.bootstrap_all()` - Main bootstrap entry point
- `RegimePriceCollector.backfill_majors_from_binance()` - Binance backfill
- `BootstrapSystem._check_backfill_needed()` - Smart backfill detection

---

## 10. Conclusion

**The system is well-designed for restarts**. The bootstrap system automatically:
- Backfills majors from Binance
- Creates regime driver positions
- Computes TA and states
- Handles missing data gracefully

**For your situation** (just started, hit data limits):
- **Fresh start is recommended** - Clean slate, bootstrap handles everything
- **Time to rebuild**: ~5-10 minutes for full backfill
- **No manual intervention needed** - Bootstrap is fully automatic

The only thing you'd need to manually recreate is **active positions** (if you have any open trades).



