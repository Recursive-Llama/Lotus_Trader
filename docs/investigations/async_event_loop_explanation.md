# Async Event Loop Issue - Detailed Explanation

## The Problem

When executing Solana sells (or buys), the code fails with:
```
RuntimeError: This event loop is already running
```

## Execution Flow

### 1. Main System (Async Context)
```
run_trade.py
  └─> TradingSystem.run() [async]
      └─> _schedule_at_interval() [async]
          └─> await asyncio.to_thread(pm_core_tick.run) [runs in thread pool]
```

**Key Point**: `asyncio.to_thread()` runs the function in a **separate thread**, but the main async event loop is still running in the main thread.

### 2. PM Core Tick (Sync Context in Thread)
```
pm_core_tick.py
  └─> PMCoreTick.run() [sync function, running in thread]
      └─> plan_actions_v4() [sync]
      └─> executor.execute() [sync]
```

**Key Point**: PM Core Tick runs in a **sync context** (thread pool), but it's being called from an async context.

### 3. PM Executor (Tries to Call Async from Sync)
```
pm/executor.py
  └─> _execute_solana_sell_token_to_usdc() [sync function]
      └─> loop = asyncio.get_event_loop()  [⚠️ PROBLEM HERE]
      └─> loop.run_until_complete(...)     [⚠️ FAILS IF LOOP IS RUNNING]
```

## The Bug

**Current Code** (lines 677-691):
```python
try:
    loop = asyncio.get_event_loop()  # Gets the MAIN event loop (which is running!)
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

result = loop.run_until_complete(...)  # ❌ FAILS: can't call run_until_complete on running loop
```

**What happens:**
1. `asyncio.get_event_loop()` returns the **main event loop** (from the async context)
2. That loop is **already running** (handling the main async tasks)
3. `run_until_complete()` **cannot** be called on a loop that's already running
4. Python raises: `RuntimeError: This event loop is already running`

## Why It's Intermittent

The error only happens when:
- The main async event loop is running (which it usually is)
- PM Core Tick runs in a thread (via `asyncio.to_thread()`)
- The thread tries to get the main loop instead of creating a new one

**Why sometimes it works:**
- If the main loop isn't running yet (startup)
- If there's no event loop at all (rare)
- The `RuntimeError` exception path creates a new loop (but this shouldn't happen if main loop exists)

## The Fix

We need to check if the loop is **running**, and if so, create a **new loop** for this operation:

```python
# Execute swap via Jupiter (async call in sync context)
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Main loop is running - create a new one for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            self.js_solana_client.execute_jupiter_swap(...)
        )
        loop.close()  # Clean up the temporary loop
    else:
        # Loop exists but not running - safe to use
        result = loop.run_until_complete(
            self.js_solana_client.execute_jupiter_swap(...)
        )
except RuntimeError:
    # No event loop exists - create one
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        self.js_solana_client.execute_jupiter_swap(...)
    )
    loop.close()
```

**Better Alternative** (using `asyncio.run()` which always creates a new loop):
```python
# Execute swap via Jupiter (async call in sync context)
# asyncio.run() always creates a new event loop
result = asyncio.run(
    self.js_solana_client.execute_jupiter_swap(
        input_mint=token_contract,
        output_mint=USDC_MINT,
        amount=tokens_raw,
        slippage_bps=slippage_bps
    )
)
```

**Note**: `asyncio.run()` is simpler but creates a new loop every time. The manual approach gives more control.

## Why This Pattern Exists

The code is trying to bridge **sync** and **async** contexts:
- PM Executor is called from sync code (PM Core Tick)
- But Jupiter client methods are async
- Need to run async code from sync context

**Better long-term solution**: Make PM Executor async, but that requires refactoring the entire PM Core Tick flow.

## Affected Code Locations

1. `src/intelligence/lowcap_portfolio_manager/pm/executor.py:677-691` - `_execute_solana_sell_token_to_usdc()`
2. `src/intelligence/lowcap_portfolio_manager/pm/executor.py:590-603` - `_execute_solana_buy_usdc_to_token()`
3. Both have the same bug pattern

