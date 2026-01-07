# Buyback Investigation & Fix

## Issue Found

**Problem**: Min gate was incorrectly applied to buyback amount instead of profit.

**User Requirements**:
- **$1.00 minimum gate on PNL** (profit_usd) - only trigger buyback if profit >= $1
- **$0.10 minimum gate on buyback amount** (swap_amount_usd) - minimum swap size

**Previous Behavior**:
- Only checked `swap_amount_usd >= $1.00` (line 300-306)
- No check on profit_usd itself
- This meant positions with $0.50 profit (10% = $0.05 buyback) would be skipped, but positions with $5 profit (10% = $0.50 buyback) would also be skipped incorrectly

## Fix Applied

### Code Changes (`pm_core_tick.py` lines 288-306)

**Before**:
```python
# Only swap if profit is positive
if profit_usd <= 0:
    return {"success": True, "skipped": True, "reason": "No profit to swap"}

# Calculate swap amount (10% of profit)
swap_amount_usd = profit_usd * (buyback_percentage / 100.0)

# Minimum swap amount check (avoid dust)
min_swap_usd = float(os.getenv("LOTUS_BUYBACK_MIN_USD", "1.0"))
if swap_amount_usd < min_swap_usd:
    return {"success": True, "skipped": True, "reason": f"Swap amount too small: ${swap_amount_usd:.2f} < ${min_swap_usd:.2f}"}
```

**After**:
```python
# Only swap if profit is positive
if profit_usd <= 0:
    return {"success": True, "skipped": True, "reason": "No profit to swap"}

# Minimum profit gate: $1.00 minimum profit required
min_profit_usd = float(os.getenv("LOTUS_BUYBACK_MIN_PROFIT_USD", "1.0"))
if profit_usd < min_profit_usd:
    return {"success": True, "skipped": True, "reason": f"Profit too small: ${profit_usd:.2f} < ${min_profit_usd:.2f} (min profit gate)"}

# Calculate swap amount (10% of profit)
swap_amount_usd = profit_usd * (buyback_percentage / 100.0)

# Minimum swap amount check (avoid dust) - $0.10 minimum on buyback amount
min_swap_usd = float(os.getenv("LOTUS_BUYBACK_MIN_USD", "0.1"))
if swap_amount_usd < min_swap_usd:
    return {"success": True, "skipped": True, "reason": f"Swap amount too small: ${swap_amount_usd:.2f} < ${min_swap_usd:.2f} (min buyback gate)"}
```

## New Environment Variables

### `LOTUS_BUYBACK_MIN_PROFIT_USD` (NEW)
- **Default**: `1.0` ($1.00)
- **Purpose**: Minimum profit required to trigger buyback
- **Example**: If profit is $0.50, buyback is skipped (even if 10% = $0.05 would be swapped)

### `LOTUS_BUYBACK_MIN_USD` (UPDATED)
- **Previous Default**: `1.0` ($1.00)
- **New Default**: `0.1` ($0.10)
- **Purpose**: Minimum buyback amount (after calculating 10% of profit)
- **Example**: If profit is $1.00, 10% = $0.10 buyback → passes both gates
- **Example**: If profit is $0.50, skipped by profit gate (never reaches this check)

## Examples

### Example 1: Profit = $0.50
- Profit: $0.50
- **Profit gate**: $0.50 < $1.00 → **SKIPPED** (min profit gate)
- Result: No buyback

### Example 2: Profit = $0.80
- Profit: $0.80
- **Profit gate**: $0.80 < $1.00 → **SKIPPED** (min profit gate)
- Result: No buyback

### Example 3: Profit = $1.00
- Profit: $1.00
- **Profit gate**: $1.00 >= $1.00 → **PASS**
- Buyback amount: $1.00 * 10% = $0.10
- **Buyback gate**: $0.10 >= $0.10 → **PASS**
- Result: **Buyback executes** ($0.10 swapped)

### Example 4: Profit = $5.00
- Profit: $5.00
- **Profit gate**: $5.00 >= $1.00 → **PASS**
- Buyback amount: $5.00 * 10% = $0.50
- **Buyback gate**: $0.50 >= $0.10 → **PASS**
- Result: **Buyback executes** ($0.50 swapped)

### Example 5: Profit = $0.90 (edge case)
- Profit: $0.90
- **Profit gate**: $0.90 < $1.00 → **SKIPPED** (min profit gate)
- Result: No buyback (even though 10% = $0.09, which is close to $0.10)

## Configuration

Update `.env` file:

```bash
# Minimum profit required to trigger buyback (default: $1.00)
LOTUS_BUYBACK_MIN_PROFIT_USD=1.0

# Minimum buyback amount (default: $0.10)
LOTUS_BUYBACK_MIN_USD=0.1
```

## Testing

To test the fix:

1. **Test with $0.50 profit**: Should be skipped (profit gate)
2. **Test with $1.00 profit**: Should execute ($0.10 buyback)
3. **Test with $5.00 profit**: Should execute ($0.50 buyback)
4. **Test with $0.99 profit**: Should be skipped (profit gate)

## Log Messages

The fix adds clearer log messages:
- `"Profit too small: $X.XX < $1.00 (min profit gate)"` - when profit is below $1
- `"Swap amount too small: $X.XX < $0.10 (min buyback gate)"` - when buyback amount is below $0.10

## Summary

✅ **Fixed**: Added $1.00 minimum profit gate  
✅ **Fixed**: Changed buyback amount minimum from $1.00 to $0.10  
✅ **Result**: Buybacks now only trigger when profit >= $1.00, and buyback amount >= $0.10

