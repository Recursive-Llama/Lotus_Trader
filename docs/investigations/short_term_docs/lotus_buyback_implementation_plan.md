# Lotus Buyback Implementation Plan

## Overview

**Goal**: When a position fully closes, swap 10% of profits to Lotus Coin, then transfer 69% of those tokens to a holding wallet.

**Complexity**: Actually **SIMPLE** - all infrastructure exists!

---

## 1. Profit Swap (USDC → Lotus Coin)

### Where It Happens
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
**Method**: `_check_position_closure()` (around line 1996)
**Trigger**: After position is marked as `watchlist` (line 1999)

### Profit Calculation
```python
# When position fully closes, use realized P&L
profit_usd = position.get('rpnl_usd', 0.0)  # Realized P&L from sells

# If rpnl_usd not available, calculate from extracted vs allocated
if profit_usd == 0:
    total_extracted = float(position.get('total_extracted_usd', 0.0))
    total_allocated = float(position.get('total_allocation_usd', 0.0))
    profit_usd = total_extracted - total_allocated

# Only swap if profit is positive
if profit_usd > 0:
    swap_amount_usd = profit_usd * 0.10  # 10% of profit
```

### Swap Execution
**Use PMExecutor** (already exists!):
```python
# Lotus Coin contract on Solana
LOTUS_CONTRACT = "Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC"

# Swap USDC → Lotus Coin on Solana
swap_result = self.executor._call_lifi_executor(
    action="swap",
    chain="solana",
    from_token="USDC",  # USDC on Solana
    to_token=LOTUS_CONTRACT,
    amount=str(int(swap_amount_usd * 1_000_000)),  # USDC has 6 decimals
    slippage=0.5,  # 0.5% slippage
    from_chain="solana",
    to_chain="solana"
)
```

**Why this works**:
- All exits already bridge to Solana USDC via Li.Fi (handled in `_execute_sell()`)
- PMExecutor has `_call_lifi_executor()` method ready to use
- Li.Fi supports Solana swaps (Jupiter integration)

### Implementation Location
Add method in `pm_core_tick.py`:
```python
def _swap_profit_to_lotus(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Swap 10% of position profit to Lotus Coin.
    
    Returns:
        Swap result dict with:
        - success: bool
        - lotus_tokens: float (amount received)
        - tx_hash: str
        - error: str (if failed)
    """
```

Call it in `_check_position_closure()` after line 2004 (after position update, before strand emission).

---

## 2. Token Transfer (69% to Holding Wallet)

### Where It Happens
**After** successful swap, transfer 69% of Lotus tokens to holding wallet.

### Transfer Execution
**Use JSSolanaClient** (already exists!):
```python
# Get Lotus tokens received from swap
lotus_tokens_received = swap_result.get('tokens_received', 0.0)

# Calculate 69% to transfer
transfer_amount = lotus_tokens_received * 0.69

# Get holding wallet from config
holding_wallet = os.getenv("LOTUS_HOLDING_WALLET")  # e.g., "AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd"

# Transfer via JSSolanaClient
if hasattr(self.executor, 'trader') and hasattr(self.executor.trader, 'js_solana_client'):
    js_client = self.executor.trader.js_solana_client
    transfer_result = await js_client.send_lotus_tokens(
        amount=transfer_amount,
        destination_wallet=holding_wallet
    )
```

**Why this works**:
- `JSSolanaClient.send_lotus_tokens()` already exists (line 454 in `js_solana_client.py`)
- Takes amount and destination wallet
- Handles token account creation if needed

### Implementation
Add to `_swap_profit_to_lotus()` method:
```python
# After successful swap
if swap_result.get('success'):
    lotus_tokens = swap_result.get('tokens_received', 0.0)
    
    # Transfer 69% to holding wallet
    transfer_amount = lotus_tokens * 0.69
    transfer_result = await self._transfer_lotus_to_holding_wallet(transfer_amount)
    
    return {
        'success': True,
        'lotus_tokens': lotus_tokens,
        'lotus_tokens_kept': lotus_tokens * 0.31,  # 31% kept in trading wallet
        'lotus_tokens_transferred': transfer_amount,  # 69% sent to holding wallet
        'swap_tx_hash': swap_result.get('tx_hash'),
        'transfer_tx_hash': transfer_result.get('tx_hash') if transfer_result else None
    }
```

---

## 3. Error Handling

**Fail gracefully**:
- If swap fails: Log error, don't break position closure
- If transfer fails: Log error, but swap already succeeded (tokens in trading wallet)
- Don't block position closure if buyback fails

**Logging**:
```python
if swap_result.get('success'):
    logger.info(f"Lotus buyback successful: {lotus_tokens:.6f} tokens from ${profit_usd:.2f} profit")
else:
    logger.warning(f"Lotus buyback failed: {swap_result.get('error')}")
```

---

## 4. Configuration

**Environment Variables**:
```bash
LOTUS_CONTRACT=Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC
LOTUS_HOLDING_WALLET=AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd
LOTUS_BUYBACK_ENABLED=1  # Enable/disable feature
LOTUS_BUYBACK_PERCENTAGE=10.0  # 10% of profit
LOTUS_TRANSFER_PERCENTAGE=69.0  # 69% to holding wallet
```

---

## 5. Database Tracking (Optional)

**Store buyback info in position**:
```python
# Add to position.features.pm_execution_history
buyback_info = {
    'lotus_buyback': {
        'profit_usd': profit_usd,
        'swap_amount_usd': swap_amount_usd,
        'lotus_tokens': lotus_tokens,
        'lotus_tokens_kept': lotus_tokens * 0.31,
        'lotus_tokens_transferred': transfer_amount,
        'swap_tx_hash': swap_result.get('tx_hash'),
        'transfer_tx_hash': transfer_result.get('tx_hash'),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
}
```

---

## Implementation Steps

1. ✅ **Add `_swap_profit_to_lotus()` method** in `pm_core_tick.py`
2. ✅ **Add `_transfer_lotus_to_holding_wallet()` method** in `pm_core_tick.py`
3. ✅ **Call `_swap_profit_to_lotus()`** in `_check_position_closure()` after position update
4. ✅ **Add error handling** (fail gracefully)
5. ✅ **Add configuration** (env vars)
6. ✅ **Test with canary position**

---

## Complexity Assessment

**Profit Swap**: ✅ **SIMPLE**
- PMExecutor already handles swaps
- Li.Fi already bridges to Solana USDC
- Just need to call `_call_lifi_executor()` with correct params

**Token Transfer**: ✅ **SIMPLE**
- `JSSolanaClient.send_lotus_tokens()` already exists
- Just need to call it with amount and wallet address

**Total Complexity**: **LOW** - All infrastructure exists, just need to wire it up!

---

## Next: Telegram Notification Redesign

After buyback is done, we'll redesign Telegram notifications for the new PM system.

