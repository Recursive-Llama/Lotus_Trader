# Execution Intent Interface Specification

**Date**: 2025-01-XX  
**Status**: Design Specification

---

## Problem Statement

Current `plan_actions_v4()` returns a dict that gets passed directly to executor. This creates tight coupling and makes it hard to:
- Add venue-specific constraints without changing PM
- Test PM independently of executors
- Evolve PM logic without breaking executors
- Handle execution constraints cleanly

---

## Proposed Solution: ExecutionIntent

**PM Core produces**: `ExecutionIntent` (universal, venue-agnostic)  
**Executor consumes**: `ExecutionIntent` → `ExecutionPlan` → `ExecutionResult`

---

## ExecutionIntent Schema

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

class ActionType(Enum):
    """Universal action types - venue-agnostic"""
    HOLD = "hold"
    ADD = "add"              # Increase position
    TRIM = "trim"            # Reduce position
    EXIT = "exit"            # Full exit
    RECLAIM = "reclaim"      # Reclaim EMA (S2 dip buy)
    EMERGENCY_EXIT = "emergency_exit"  # Emergency exit (S0, reclaimed EMA333)

@dataclass
class ExecutionIntent:
    """Universal execution intent from PM Core - venue-agnostic"""
    
    # Core action
    action: ActionType
    
    # Sizing
    size_frac: float  # Fraction of position/allocation (0.0-1.0)
    
    # Urgency/Priority
    urgency: str  # "low", "medium", "high", "critical"
    priority: int  # 0-100 (higher = more urgent)
    
    # Constraints (optional, executor can override)
    max_slippage_bps: Optional[int] = None  # Max slippage in basis points
    reduce_only: bool = False  # Only reduce position (no new entries)
    post_only: bool = False  # Post-only order (maker only)
    
    # Context for learning/audit
    reason_codes: List[str]  # ["buy_flag", "s2_dip", "high_a_score"]
    state: str  # Current uptrend state (S0-S4)
    prev_state: str  # Previous state
    a_final: float  # Final aggressiveness score
    e_final: float  # Final exit assertiveness score
    
    # Metadata
    position_id: str
    token_contract: str
    token_chain: str  # Actually "venue namespace" (see naming discussion)
    book_id: str
    timeframe: str
    
    # Optional: PM-level risk constraints
    max_leverage: Optional[float] = None  # If PM wants to cap leverage
    risk_reason: Optional[str] = None  # Why risk constraint applied
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage/logging"""
        return {
            "action": self.action.value,
            "size_frac": self.size_frac,
            "urgency": self.urgency,
            "priority": self.priority,
            "max_slippage_bps": self.max_slippage_bps,
            "reduce_only": self.reduce_only,
            "post_only": self.post_only,
            "reason_codes": self.reason_codes,
            "state": self.state,
            "prev_state": self.prev_state,
            "a_final": self.a_final,
            "e_final": self.e_final,
            "position_id": self.position_id,
            "token_contract": self.token_contract,
            "token_chain": self.token_chain,
            "book_id": self.book_id,
            "timeframe": self.timeframe,
            "max_leverage": self.max_leverage,
            "risk_reason": self.risk_reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionIntent":
        """Create from dict"""
        return cls(
            action=ActionType(data["action"]),
            size_frac=data["size_frac"],
            urgency=data["urgency"],
            priority=data["priority"],
            max_slippage_bps=data.get("max_slippage_bps"),
            reduce_only=data.get("reduce_only", False),
            post_only=data.get("post_only", False),
            reason_codes=data.get("reason_codes", []),
            state=data["state"],
            prev_state=data.get("prev_state", ""),
            a_final=data["a_final"],
            e_final=data["e_final"],
            position_id=data["position_id"],
            token_contract=data["token_contract"],
            token_chain=data["token_chain"],
            book_id=data["book_id"],
            timeframe=data["timeframe"],
            max_leverage=data.get("max_leverage"),
            risk_reason=data.get("risk_reason"),
        )
```

---

## Executor Interface

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class ExecutionStatus(Enum):
    """Execution result status"""
    SUCCESS = "success"
    SKIPPED = "skipped"  # Executor chose to skip (market closed, constraints, etc.)
    ERROR = "error"
    PARTIAL = "partial"  # Partial execution

@dataclass
class ExecutionPlan:
    """Venue-specific execution plan (after constraints applied)"""
    action: ActionType
    order_type: str  # "market", "limit", "stop", etc. (venue-specific)
    size: float  # Actual size after rounding/constraints
    price: Optional[float]  # Limit price if applicable
    leverage: float  # Actual leverage (0.0 for spot)
    constraints_applied: List[str]  # ["market_hours", "min_notional", "leverage_cap"]
    skip_reason: Optional[str] = None  # If skipped, why

@dataclass
class ExecutionResult:
    """Execution result from venue"""
    status: ExecutionStatus
    plan: Optional[ExecutionPlan] = None  # Plan that was executed (or would be)
    tx_hash: Optional[str] = None  # Transaction hash (on-chain) or order ID (CEX)
    tokens_bought: Optional[float] = None
    tokens_sold: Optional[float] = None
    price: Optional[float] = None  # Execution price
    slippage_bps: Optional[int] = None
    fees_usd: Optional[float] = None
    skip_reason: Optional[str] = None  # If skipped
    error: Optional[str] = None  # If error
    metadata: Dict[str, Any] = None  # Venue-specific metadata

class BaseExecutor:
    """Base executor interface - all executors implement this"""
    
    def prepare(
        self, 
        intent: ExecutionIntent, 
        position: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Convert ExecutionIntent to ExecutionPlan.
        
        Applies all venue-specific constraints:
        - Market hours
        - Min notional
        - Rounding rules
        - Leverage caps
        - Order type selection
        - Reduce-only rules
        
        Returns ExecutionPlan or raises SkipExecution exception.
        """
        raise NotImplementedError
    
    def execute(
        self, 
        plan: ExecutionPlan, 
        position: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute the plan on the venue.
        
        Returns ExecutionResult with status, tx_hash, etc.
        """
        raise NotImplementedError
    
    def can_trade_now(self, position: Dict[str, Any]) -> bool:
        """
        Check if venue allows trading right now.
        
        This is a convenience method - prepare() will also check this.
        """
        raise NotImplementedError
```

---

## PM Core Changes

**Current:**
```python
def plan_actions_v4(...) -> List[Dict[str, Any]]:
    # Returns raw dict
    return [{"decision_type": "add", "size_frac": 0.5, ...}]
```

**Proposed:**
```python
def plan_actions_v4(...) -> List[ExecutionIntent]:
    # Returns ExecutionIntent objects
    intents = []
    
    if should_add:
        intents.append(ExecutionIntent(
            action=ActionType.ADD,
            size_frac=0.5,
            urgency="medium",
            priority=50,
            reason_codes=["buy_flag", "s2_dip"],
            state="S2",
            prev_state="S1",
            a_final=a_final,
            e_final=e_final,
            position_id=position["id"],
            token_contract=position["token_contract"],
            token_chain=position["token_chain"],
            book_id=position["book_id"],
            timeframe=position["timeframe"],
        ))
    
    return intents
```

---

## Executor Implementation Example

```python
class HyperliquidExecutor(BaseExecutor):
    def prepare(self, intent: ExecutionIntent, position: Dict[str, Any]) -> ExecutionPlan:
        """Convert intent to Hyperliquid-specific plan"""
        
        # Check market hours (24/7 for Hyperliquid, but check for maintenance)
        if not self._is_market_open():
            raise SkipExecution(reason="market_maintenance")
        
        # Check constraints
        if intent.reduce_only and intent.action == ActionType.ADD:
            raise SkipExecution(reason="reduce_only_constraint")
        
        # Apply leverage cap
        leverage = min(intent.max_leverage or 0.0, self._max_leverage_for_symbol(intent.token_contract))
        
        # Calculate size after constraints
        notional_usd = position["total_allocation_usd"] * intent.size_frac
        size = self._calculate_contract_size(intent.token_contract, notional_usd, leverage)
        
        # Round to contract size
        size = self._round_to_contract_size(size, intent.token_contract)
        
        # Check min notional
        if notional_usd < self._min_notional(intent.token_contract):
            raise SkipExecution(reason="below_min_notional")
        
        # Select order type
        order_type = "market" if intent.urgency == "critical" else "limit"
        
        return ExecutionPlan(
            action=intent.action,
            order_type=order_type,
            size=size,
            price=None,  # Market order
            leverage=leverage,
            constraints_applied=["leverage_cap", "contract_rounding", "min_notional"],
        )
    
    def execute(self, plan: ExecutionPlan, position: Dict[str, Any]) -> ExecutionResult:
        """Execute on Hyperliquid"""
        try:
            # Call Hyperliquid API
            result = self._place_order(
                symbol=position["token_contract"],
                side="B" if plan.action == ActionType.ADD else "S",
                size=plan.size,
                leverage=plan.leverage,
                order_type=plan.order_type,
            )
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                plan=plan,
                tx_hash=result["order_id"],
                tokens_bought=plan.size if plan.action == ActionType.ADD else None,
                tokens_sold=plan.size if plan.action == ActionType.TRIM else None,
                price=result["price"],
                slippage_bps=result.get("slippage_bps"),
                fees_usd=result.get("fees_usd"),
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                plan=plan,
                error=str(e),
            )
```

---

## PM Core Tick Changes

**Current:**
```python
decision = plan_actions_v4(...)
if decision['decision_type'] != 'hold':
    executor = executor_factory.get_executor(...)
    result = executor.execute(decision, position)
```

**Proposed:**
```python
intents = plan_actions_v4(...)
for intent in intents:
    if intent.action == ActionType.HOLD:
        continue
    
    executor = executor_factory.get_executor(intent.token_chain, intent.book_id)
    if not executor:
        logger.warning(f"No executor for {intent.token_chain}/{intent.book_id}")
        continue
    
    try:
        plan = executor.prepare(intent, position)
        result = executor.execute(plan, position)
        
        # Handle result
        if result.status == ExecutionStatus.SKIPPED:
            logger.info(f"Skipped execution: {result.skip_reason}")
        elif result.status == ExecutionStatus.SUCCESS:
            # Update position
            self._update_position_after_execution(position, result)
    except SkipExecution as e:
        logger.info(f"Execution skipped: {e.reason}")
```

---

## Benefits

1. **Clean Separation**: PM produces universal intents, executor handles all constraints
2. **Testable**: Can test PM independently (just check intents)
3. **Evolvable**: PM can evolve without breaking executors
4. **Auditable**: Clear reason codes and constraints applied
5. **Flexible**: Executors can skip cleanly with reasons

---

## Migration Path

1. **Phase 1**: Create `ExecutionIntent` class, keep `plan_actions_v4()` returning dicts
2. **Phase 2**: Add `ExecutionIntent.from_dict()` converter, convert in PM Core Tick
3. **Phase 3**: Update `plan_actions_v4()` to return `ExecutionIntent` objects
4. **Phase 4**: Update executors to use `prepare()` / `execute()` pattern

---

## Next Steps

1. Review current `plan_actions_v4()` output schema
2. Finalize `ExecutionIntent` fields
3. Implement `BaseExecutor` interface
4. Update one executor (Hyperliquid) as proof of concept
5. Migrate PM Core Tick to use new interface

