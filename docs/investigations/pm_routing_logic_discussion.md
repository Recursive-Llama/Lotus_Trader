# PM Routing Logic - Deep Dive Discussion

**Date**: 2025-01-XX  
**Focus**: How should PM Core Tick route positions to appropriate PM modules?

---

## Current Architecture

**PM Core Tick Flow:**
```
Every 5 minutes (per timeframe):
1. Fetch positions: WHERE timeframe = '1h' AND status IN ('watchlist', 'active')
2. For each position:
   - Compute A/E scores (from regime engine)
   - Call plan_actions_v4() → returns decision
   - Call executor.execute(decision, position)
   - Update position state
```

**Current Executor:**
- `PMExecutor` - Only handles Solana
- Hardcoded: `allowed_chains = ['solana']`
- Uses Jupiter for swaps

---

## The Routing Question

**Problem**: How to route Hyperliquid positions to Hyperliquid executor while keeping Solana positions with Solana executor?

**Key Constraint**: Trading logic is **identical** (long-only, same signals, same A/E logic)
- Only difference is **execution venue**

---

## Option 1: Simple Conditional in PM Core Tick (Simplest)

**Approach**: Add conditional logic in existing PM Core Tick

```python
class PMCoreTick:
    def __init__(self, timeframe):
        self.executor = PMExecutor(...)  # Solana
        self.hyperliquid_executor = HyperliquidExecutor(...)  # New
    
    def _process_position(self, position):
        # ... compute A/E scores ...
        decision = plan_actions_v4(...)
        
        # Route to appropriate executor
        if position['token_chain'] == 'hyperliquid':
            executor = self.hyperliquid_executor
        else:
            executor = self.executor
        
        result = executor.execute(decision, position)
        # ... update position ...
```

**Pros:**
- ✅ Minimal changes to existing code
- ✅ Same PM logic for both venues
- ✅ Easy to test (just swap executor)
- ✅ Fast to implement

**Cons:**
- ❌ PM Core Tick becomes aware of venue differences
- ❌ Harder to add more venues later (nested if/else)
- ❌ Mixing concerns (routing + PM logic)

**Best For**: Initial testing, proof of concept

---

## Option 2: PM Module Pattern (Clean Separation)

**Approach**: Extract PM logic into modules, PM Core Tick becomes router

```python
# Base PM Module
class PMModule:
    def process_position(self, position, a_final, e_final, regime_context):
        """Process a single position - returns decision"""
        decision = plan_actions_v4(position, a_final, e_final, ...)
        return decision
    
    def execute_decision(self, decision, position):
        """Execute decision using venue-specific executor"""
        raise NotImplementedError

# Solana PM Module
class PM_Spot(PMModule):
    def __init__(self):
        self.executor = PMExecutor(...)
    
    def execute_decision(self, decision, position):
        return self.executor.execute(decision, position)

# Hyperliquid PM Module
class PM_Hyperliquid_Spot(PMModule):
    def __init__(self):
        self.executor = HyperliquidExecutor(...)
    
    def execute_decision(self, decision, position):
        return self.executor.execute(decision, position)

# PM Core Tick (Router)
class PMCoreTick:
    def __init__(self, timeframe):
        self.pm_modules = {
            ('solana', 'social'): PM_Spot(),
            ('hyperliquid', 'spot'): PM_Hyperliquid_Spot(),
        }
    
    def run(self):
        positions = self._fetch_positions()
        for position in positions:
            key = (position['token_chain'], position['book_id'])
            pm_module = self.pm_modules.get(key)
            
            if not pm_module:
                logger.warning(f"No PM module for {key}")
                continue
            
            # Compute A/E scores (shared logic)
            a_final, e_final = compute_ae_v2(...)
            regime_context = self._get_regime_context()
            
            # PM module processes position
            decision = pm_module.process_position(position, a_final, e_final, regime_context)
            
            if decision['decision_type'] != 'hold':
                result = pm_module.execute_decision(decision, position)
                # ... update position ...
```

**Pros:**
- ✅ Clean separation of concerns
- ✅ Easy to add new venues (just add module)
- ✅ PM Core Tick is pure router
- ✅ Each module is self-contained
- ✅ Testable in isolation

**Cons:**
- ❌ More code structure (but cleaner)
- ❌ Slight overhead (module lookup)
- ❌ Need to extract shared PM logic

**Best For**: Production, long-term maintainability

---

## Option 3: Executor Factory Pattern (Hybrid)

**Approach**: Keep PM logic unified, route only at executor level

```python
class ExecutorFactory:
    def __init__(self):
        self.executors = {
            'solana': PMExecutor(...),
            'hyperliquid': HyperliquidExecutor(...),
        }
    
    def get_executor(self, token_chain, book_id):
        # Could add book_id logic here for perps later
        return self.executors.get(token_chain)

class PMCoreTick:
    def __init__(self, timeframe):
        self.executor_factory = ExecutorFactory()
        # ... rest of PM logic unchanged ...
    
    def _process_position(self, position):
        # ... compute A/E, plan_actions_v4 ...
        
        executor = self.executor_factory.get_executor(
            position['token_chain'],
            position['book_id']
        )
        
        if not executor:
            logger.warning(f"No executor for {position['token_chain']}")
            return
        
        result = executor.execute(decision, position)
```

**Pros:**
- ✅ Minimal changes to PM Core Tick
- ✅ Executor routing is isolated
- ✅ Easy to test
- ✅ Less code than Option 2

**Cons:**
- ❌ Still mixing routing with PM logic
- ❌ Less flexible for venue-specific PM logic later

**Best For**: When PM logic is truly identical across venues

---

## Option 4: Separate PM Core Tick Instances (Parallel)

**Approach**: Run separate PM Core Tick for each venue

```python
# Scheduler
def schedule_pm_ticks():
    # Solana PM
    pm_solana = PMCoreTick(timeframe='1h', venue_filter={'token_chain': 'solana'})
    schedule.every(5).minutes.do(pm_solana.run)
    
    # Hyperliquid PM
    pm_hyperliquid = PMCoreTick(timeframe='1h', venue_filter={'token_chain': 'hyperliquid'})
    schedule.every(5).minutes.do(pm_hyperliquid.run)

class PMCoreTick:
    def __init__(self, timeframe, venue_filter=None):
        self.venue_filter = venue_filter
        if venue_filter and 'token_chain' in venue_filter:
            if venue_filter['token_chain'] == 'hyperliquid':
                self.executor = HyperliquidExecutor(...)
            else:
                self.executor = PMExecutor(...)
        else:
            self.executor = PMExecutor(...)
    
    def _fetch_positions(self):
        query = self.sb.table('lowcap_positions').select('*')
        if self.venue_filter:
            for key, value in self.venue_filter.items():
                query = query.eq(key, value)
        return query.execute().data
```

**Pros:**
- ✅ Complete isolation between venues
- ✅ Can run at different frequencies if needed
- ✅ Easy to scale (separate processes)

**Cons:**
- ❌ Code duplication (PM logic runs twice)
- ❌ More scheduler complexity
- ❌ Harder to share state/cache

**Best For**: When venues need different processing frequencies

---

## Recommendation Matrix

| Scenario | Recommended Option | Reason |
|----------|-------------------|---------|
| **Initial Testing** | Option 1 (Simple Conditional) | Fastest to implement, validate executor works |
| **Production (Identical Logic)** | Option 3 (Executor Factory) | Clean routing, minimal changes |
| **Production (Future Venue-Specific Logic)** | Option 2 (PM Modules) | Most flexible, cleanest architecture |
| **Different Processing Frequencies** | Option 4 (Separate Instances) | Only if venues need different schedules |

---

## My Recommendation: Start with Option 1, Evolve to Option 3

**Phase 1: Testing (Option 1)**
```python
# Quick test to validate executor
if position['token_chain'] == 'hyperliquid':
    executor = self.hyperliquid_executor
else:
    executor = self.executor
```

**Phase 2: Production (Option 3)**
```python
# Clean executor routing
executor = self.executor_factory.get_executor(
    position['token_chain'],
    position['book_id']
)
```

**Why This Path:**
1. **Fast to test**: Option 1 gets you testing executor immediately
2. **Easy migration**: Option 1 → Option 3 is trivial refactor
3. **Future-proof**: Option 3 can evolve to Option 2 if needed
4. **Low risk**: Minimal changes, easy to rollback

---

## Questions to Answer

1. **Do you want venue-specific PM logic eventually?**
   - If yes → Option 2 (PM Modules)
   - If no → Option 3 (Executor Factory)

2. **Do venues need different processing frequencies?**
   - If yes → Option 4 (Separate Instances)
   - If no → Option 1/2/3

3. **How quickly do you need to test?**
   - Fast → Option 1
   - Can wait → Option 2/3

4. **Will you add more venues soon?**
   - Yes → Option 2 (most flexible)
   - No → Option 1/3 (simpler)

---

## Implementation Example: Option 1 (Testing)

```python
# In pm_core_tick.py
class PMCoreTick:
    def __init__(self, timeframe: str = "1h", learning_system=None) -> None:
        # ... existing init ...
        
        # Initialize executors
        self.executor = PMExecutor(trader=None, sb_client=self.sb)
        
        # Initialize Hyperliquid executor (if enabled)
        self.hyperliquid_executor = None
        if os.getenv("HYPERLIQUID_EXECUTOR_ENABLED", "0") == "1":
            from src.intelligence.lowcap_portfolio_manager.pm.hyperliquid_executor import HyperliquidExecutor
            self.hyperliquid_executor = HyperliquidExecutor(sb_client=self.sb)
    
    def _get_executor_for_position(self, position: Dict[str, Any]):
        """Route to appropriate executor based on position venue."""
        token_chain = position.get('token_chain', '').lower()
        
        if token_chain == 'hyperliquid':
            if not self.hyperliquid_executor:
                logger.warning("Hyperliquid position but executor not enabled")
                return None
            return self.hyperliquid_executor
        else:
            return self.executor
    
    def _process_position(self, position: Dict[str, Any]) -> None:
        # ... existing A/E computation ...
        decision = plan_actions_v4(...)
        
        if decision['decision_type'] == 'hold':
            return
        
        # Route to appropriate executor
        executor = self._get_executor_for_position(position)
        if not executor:
            logger.warning(f"No executor for position {position.get('id')}")
            return
        
        # Execute (same interface for both executors)
        result = executor.execute(decision, position)
        
        # ... existing position update logic ...
```

**Changes:**
- ✅ Add `_get_executor_for_position()` method
- ✅ Initialize Hyperliquid executor (if enabled)
- ✅ Route before execution
- ✅ Everything else stays the same

**Testing:**
1. Set `HYPERLIQUID_EXECUTOR_ENABLED=1`
2. Create test position: `token_chain='hyperliquid'`, `book_id='spot'`
3. Verify routing works
4. Test executor in dry-run mode

---

## Next Steps

1. **Decide on routing approach** (recommend Option 1 for testing)
2. **Implement executor routing** (simple conditional)
3. **Test with dry-run executor**
4. **Validate end-to-end flow**
5. **Refactor to Option 3 if needed** (easy migration)

---

## Summary

**For Testing**: Option 1 (Simple Conditional)
- Fastest to implement
- Validates executor works
- Easy to test

**For Production**: Option 3 (Executor Factory)
- Clean routing
- Minimal changes
- Easy to extend

**For Future**: Option 2 (PM Modules)
- Most flexible
- Cleanest architecture
- Best for multiple venues with different logic

**Recommendation**: Start with Option 1, evolve to Option 3 after testing validates executor works.

