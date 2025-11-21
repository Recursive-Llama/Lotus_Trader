# PM Execution Flow Analysis

## Current Understanding (What We're Building)

### Role Separation

**Uptrend Engine**:
- **Role**: Technical analysis only
- **Inputs**: OHLC data, TA indicators, geometry
- **Outputs**: Flags and signals (`buy_signal`, `buy_flag`, `first_dip_buy_flag`, `trim_flag`, `emergency_exit`, etc.)
- **Does NOT have**: A/E scores, position sizing logic, allocation info
- **Does NOT make**: Trading decisions

**Portfolio Manager**:
- **Role**: Decision making and execution
- **Inputs**: Engine flags + A/E scores + position state + allocation info
- **Outputs**: Trading decisions (`add`, `trim`, `demote`, `hold`)
- **Has**: Position sizing logic, A/E scores, allocation multipliers
- **Makes**: Final trading decisions

### Correct Flow

```
1. Uptrend Engine (every 5 min)
   └─> Reads OHLC data
   └─> Checks price conditions (price <= EMA144, abs(price - EMA60) <= ATR, etc.)
   └─> Sets flags: buy_signal=True, buy_flag=True, etc.
   └─> Writes to features.uptrend_engine_v4

2. PM Core Tick (every 5 min)
   └─> Reads features.uptrend_engine_v4 (engine flags)
   └─> Computes A/E scores (from phase, cut_pressure, position state)
   └─> Calls plan_actions_v4() which:
       - Takes engine flags + A/E scores
       - Applies position sizing logic
       - Applies allocation risk multipliers
       - Makes decision: add/trim/demote/hold
   └─> ??? (execution - what's best?)

3. Execution
   └─> ??? (how should this work?)
```

## Execution Flow Options

### Option 1: Direct Call (Recommended) ✅

**Flow**:
```
PM Core Tick
  └─> plan_actions_v4() returns decisions
  └─> For each non-hold decision:
      ├─> Direct call: executor.execute(decision)
      └─> Write strand after execution (async/non-blocking)
```

**Pros**:
- ✅ **Most reliable** - no indirection, no event system to fail
- ✅ **Fastest** - direct function call
- ✅ **Simplest** - fewest moving parts
- ✅ **Clear error handling** - exceptions propagate directly
- ✅ **Still has audit trail** - strands written after (doesn't need to block)

**Cons**:
- ⚠️ Tight coupling (PM knows about executor)
- ⚠️ Can't easily add subscribers (but can add logging/metrics as direct calls)

**Implementation**:
```python
# In pm_core_tick.py
def run(self):
    for position in positions:
        decisions = plan_actions_v4(position, a_final, e_final, phase)
        for decision in decisions:
            if decision["decision_type"] != "hold":
                # Execute immediately
                executor.execute(decision, position)
                # Write strand after (non-blocking)
                asyncio.create_task(self._write_strand_async(decision, position))
```

### Option 2: Events (Current)

**Flow**:
```
PM Core Tick
  └─> plan_actions_v4() returns decisions
  └─> Write strands to DB
  └─> Emit "decision_approved" event (in-process dict)
  └─> Executor subscribes and executes
```

**Pros**:
- ✅ Separation of concerns
- ✅ Can add more subscribers (logging, metrics)
- ✅ Event overhead is minimal (dict lookup)

**Cons**:
- ⚠️ Extra indirection (event bus)
- ⚠️ Less reliable (event system could fail silently)
- ⚠️ Harder to debug (indirect flow)
- ⚠️ Naming issue: "decision_approved" doesn't make sense for buys

**Issues**:
- "decision_approved" is a bad name - what does "approved" mean for a buy?
- Better name: "pm_decision" or "action_ready" or just emit the decision

### Option 3: Strands Only (Polling)

**Flow**:
```
PM Core Tick
  └─> plan_actions_v4() returns decisions
  └─> Write strands to DB
  └─> Executor polls ad_strands table
  └─> Executes when finds new decisions
```

**Pros**:
- ✅ Decoupled
- ✅ Audit trail

**Cons**:
- ❌ Slowest (polling delay)
- ❌ More complex (polling logic, state tracking)
- ❌ Not recommended

### Option 4: Conditional Execution

**Flow**:
```
PM Core Tick
  └─> plan_actions_v4() returns conditional decisions
  └─> Write "execute when price hits EMA60" to queue
  └─> Price monitor tracks conditions
  └─> Executes when condition met
```

**Pros**:
- ✅ More precise timing

**Cons**:
- ❌ Much more complex
- ❌ What if condition never met? (stale orders)
- ❌ Engine already checks conditions - redundant
- ❌ Not recommended (engine checks frequently enough)

## Recommendation: Direct Call

**Why Direct Call is Best**:

1. **Most Reliable**: 
   - No event system to fail
   - Direct error propagation
   - Easier to debug

2. **Fastest**:
   - Direct function call
   - No DB polling
   - No event overhead

3. **Simplest**:
   - Fewest moving parts
   - Clear flow
   - Easy to understand

4. **Still Has Audit Trail**:
   - Strands written after execution (non-blocking)
   - Learning system can use strands later
   - Doesn't need to block execution

5. **We're Building New**:
   - Can design it right from the start
   - No legacy constraints
   - Can add complexity later if needed

## Implementation Plan

### Phase 1: Direct Call Architecture

```python
# In pm_core_tick.py
class PMCoreTick:
    def __init__(self, executor=None):
        self.executor = executor  # Pass executor instance
    
    def run(self):
        for position in positions:
            decisions = plan_actions_v4(position, a_final, e_final, phase)
            for decision in decisions:
                if decision["decision_type"] != "hold":
                    # Execute immediately (direct call)
                    try:
                        result = self.executor.execute(decision, position)
                        # Write strand after execution (with result)
                        self._write_strand_after_execution(decision, position, result)
                    except Exception as e:
                        # Log error, still write strand (with error info)
                        self._write_strand_after_execution(decision, position, {"error": str(e)})
                else:
                    # Hold decisions - just write strand
                    self._write_strand(decision, position)
```

### Phase 2: Strand Writing (Non-Blocking)

```python
def _write_strand_after_execution(self, decision, position, execution_result):
    """Write strand after execution with execution result"""
    strand = {
        "token": position["token_contract"],
        "ts": datetime.now(timezone.utc).isoformat(),
        "decision_type": decision["decision_type"],
        "size_frac": decision["size_frac"],
        "a_value": a_final,
        "e_value": e_final,
        "reasons": decision["reasons"],
        "execution_result": execution_result,  # tx_hash, error, etc.
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    # Write async (non-blocking)
    asyncio.create_task(self._write_strand_async(strand))
```

### Phase 3: Executor Interface

```python
# In pm/executor.py
class PMExecutor:
    def execute(self, decision: Dict, position: Dict) -> Dict:
        """Execute PM decision directly"""
        decision_type = decision["decision_type"]
        token = position["token_contract"]
        chain = position["token_chain"]
        
        # Get latest price
        price_usd, price_native = self._get_latest_price(token, chain)
        
        # Execute based on type
        if decision_type in ["add", "trend_add"]:
            return self._execute_buy(decision, position, price_usd)
        elif decision_type in ["trim", "trail"]:
            return self._execute_sell(decision, position, price_usd)
        elif decision_type == "demote":
            return self._execute_exit(decision, position, price_usd)
        
        return {"status": "skipped", "reason": "unknown_decision_type"}
```

## Naming Improvements

**Current**: `decision_approved` event
**Better**: 
- `pm_action` (action ready to execute)
- `pm_decision` (decision made)
- Or just remove events, use direct call

## Questions to Answer

1. **Does learning system need strands before or after execution?**
   - Probably after (with execution results)
   - Learning system can analyze: decision → execution → outcome

2. **Do we need multiple subscribers?**
   - Currently: Just executor
   - Future: Logging, metrics
   - Can add as direct calls if needed

3. **What about error handling?**
   - Direct call: Exceptions propagate, easier to handle
   - Events: Can fail silently, harder to debug

4. **What about idempotency?**
   - Direct call: Can check in executor before executing
   - Events: Currently uses idempotency cache (3 min window)

## Final Recommendation

**Use Direct Call Architecture**:
- PM Core Tick → plan_actions_v4() → executor.execute() → write strand after
- Simple, reliable, fast
- Strands for learning/audit (written after execution with results)
- Can add complexity later if needed (events, conditional execution, etc.)


