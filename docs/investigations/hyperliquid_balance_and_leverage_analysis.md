# Hyperliquid Balance & Leverage Management Analysis

**Date**: 2025-01-XX  
**Status**: Analysis - No Changes Yet  
**Purpose**: Investigate Hyperliquid USDC balance tracking and leverage management

---

## 1. Hyperliquid USDC Balance Tracking

### Current State
- **PM Core Tick** calculates `usd_alloc_remaining` using only Solana USDC balance (line 2378)
- **Hyperliquid margin/collateral** is NOT included in allocation calculations
- This **undercounts available capital** for Hyperliquid positions

### How Hyperliquid Works
- Capital is **deposited as margin/collateral** on Hyperliquid (separate from Solana USDC)
- Margin is used to back positions (collateral for perpetuals)
- `user_state` API returns account state including:
  - `crossMarginSummary.totalRawUsd` - Total account value (margin + unrealized PnL)
  - `crossMarginSummary.accountValue` - Account value
  - Individual position `marginUsed` - Margin allocated to each position

### Solution: Add Hyperliquid Balance to `wallet_balances`

**Option A: Add `chain='hyperliquid'` row** ✅ RECOMMENDED
- Add new row: `chain='hyperliquid'`, `usdc_balance=<margin_balance>`
- Query Hyperliquid margin via `user_state` API
- Update `_recalculate_pnl_fields` to use Hyperliquid balance for Hyperliquid positions
- Include in balance snapshots (already sums all `usdc_balance` from all chains)

**Implementation Steps:**
1. Create function to query Hyperliquid margin balance via `user_state` API
2. Add/update `wallet_balances` row for `chain='hyperliquid'`
3. Update `_recalculate_pnl_fields` to:
   - For Hyperliquid positions: Use Hyperliquid USDC balance
   - For Solana positions: Use Solana USDC balance
4. Update balance snapshot job (already works - sums all chains)

**Balance Query:**
```python
# In HyperliquidExecutor or new balance job
state = self._info.user_state(self._account_address)
cross_margin = state.get("crossMarginSummary", {})
account_value = float(cross_margin.get("accountValue", 0.0))
# Or use totalRawUsd? Need to verify which represents available margin
```

**PM Core Tick Update:**
```python
# In _recalculate_pnl_fields
if token_chain == "hyperliquid":
    # Get Hyperliquid USDC balance (margin)
    wallet_result = self.sb.table("wallet_balances").select("usdc_balance").eq("chain", "hyperliquid").limit(1).execute()
    wallet_balance = float(wallet_result.data[0].get("usdc_balance", 0.0)) if wallet_result.data else 0.0
else:
    # Get Solana USDC balance (home chain)
    wallet_result = self.sb.table("wallet_balances").select("usdc_balance").eq("chain", home_chain).limit(1).execute()
    wallet_balance = float(wallet_result.data[0].get("usdc_balance", 0.0)) if wallet_result.data else 0.0
```

---

## 2. Leverage Management on Hyperliquid

### Current State
- **No leverage parameter** in `HyperliquidExecutor.execute_market_order()` or `execute_limit_order()`
- Orders are placed **without explicit leverage setting**
- Leverage is **per-position**, not per-order

### How Hyperliquid Leverage Works

**Key Facts:**
1. **Leverage is set per position**, not per order
2. **Default leverage**: When opening a new position, leverage defaults to **1.0x** (no leverage) if not specified
3. **Leverage can be changed** after position is opened (via separate API call)
4. **Margin modes**:
   - **Cross margin**: Uses entire account balance as collateral (default)
   - **Isolated margin**: Allocates specific collateral to position (some assets require this)

**From API Spec:**
- Position response shows: `"leverage": {"value": "1.0"}` - Current leverage for that position
- `maxLeverage` in asset metadata: Maximum allowed leverage (e.g., BTC = 40x)
- Some assets have `onlyIsolated: true` - Must use isolated margin

### Current Implementation Gap

**Issue**: We're not setting leverage explicitly, so:
- New positions default to **1.0x** (which is what we want initially)
- But we have **no way to change leverage** later if needed
- We're not tracking leverage per position in our database

### Questions to Answer

1. **Do we want to manage leverage?**
   - Option A: Always 1x (no leverage) - simplest, safest
   - Option B: Allow leverage changes based on PM signals - more complex
   - Option C: Track leverage but don't change it automatically

2. **How to set leverage?**
   - Hyperliquid SDK likely has a method to update position leverage
   - Need to check SDK docs for `update_leverage()` or similar

3. **Isolated vs Cross Margin?**
   - Most assets use **cross margin** (default)
   - Some assets require **isolated margin** (`onlyIsolated: true`)
   - For isolated: Need to allocate specific collateral to position
   - For cross: All positions share account balance

### Recommendation

**For MVP (Start Simple):**
1. **Always use 1x leverage** (no leverage) - matches your requirement
2. **Use cross margin** (default) - simpler, no collateral allocation needed
3. **Track leverage in position metadata** (for future use):
   ```python
   position["features"]["hyperliquid_metadata"]["leverage"] = 1.0
   position["features"]["hyperliquid_metadata"]["margin_mode"] = "cross"
   ```

**For Future Enhancement:**
- Add leverage management if PM signals suggest it
- Add isolated margin support for assets that require it
- Track leverage changes in execution history

### Implementation Notes

**Current Order Placement:**
- ✅ No leverage parameter needed - defaults to 1x for new positions
- ✅ Cross margin is default - no configuration needed
- ⚠️ Need to verify: Does SDK order() call set leverage, or is it separate?

**Position Tracking:**
- Query `user_state` to get current leverage per position
- Store in position metadata for reference
- Use for risk calculations (liquidation price, etc.)

---

## 3. Balance Snapshot Integration

### Current State
- `BalanceSnapshotJob.capture_snapshot()` already sums all `usdc_balance` from all chains (line 33)
- ✅ **Already works** - just need to add Hyperliquid row to `wallet_balances`

### What Needs to Happen
1. **Create balance update job** (or add to existing price collector):
   - Query Hyperliquid margin balance via `user_state` API
   - Update `wallet_balances` row for `chain='hyperliquid'`
   - Run periodically (same frequency as Solana balance updates)

2. **Balance snapshot will automatically include it** (no changes needed)

---

## Summary

### Hyperliquid USDC Balance
- ✅ **Solution**: Add `chain='hyperliquid'` row to `wallet_balances`
- ✅ **Update PM Core Tick** to use Hyperliquid balance for Hyperliquid positions
- ✅ **Balance snapshots** already work (sums all chains)

### Leverage Management
- ✅ **Current**: Defaults to 1x (no leverage) - matches requirement
- ✅ **Margin Mode**: Cross margin (default) - no changes needed
- ⚠️ **Future**: Add leverage tracking in position metadata (optional)
- ⚠️ **Future**: Add leverage management API if needed later

### Next Steps
1. Create function to query Hyperliquid margin balance
2. Add balance update job (or integrate into existing)
3. Update PM Core Tick allocation calculation
4. Test with real Hyperliquid account
