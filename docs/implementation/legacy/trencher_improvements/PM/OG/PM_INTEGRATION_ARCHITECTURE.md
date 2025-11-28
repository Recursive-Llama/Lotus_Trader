# PM Integration Architecture & Implementation Plan

## 🎯 **Current System Reality Check**

### **What Actually Exists**
1. **PM runs on scheduled ticks** (`PMCoreTick` hourly) + event-driven updates
2. **No Learning System → PM trigger** - PM is completely separate from the decision flow
3. **Price monitoring exists** but is NOT wired to PM decisions
4. **Native token amounts** throughout (SOL, ETH, BNB) - USD only for reporting
5. **Database schema** uses `lowcap_positions_schema.sql` with `total_allocation_pct` from DM

### **What's Missing (The Integration Gap)**
1. **Learning System → PM trigger** - DM creates positions, PM should manage them
2. **Price monitoring → PM decisions** - PM needs to react to price/TA changes
3. **PM → Execution conditions** - PM needs to output specific execution conditions
4. **Price Monitor → Execution** - Price Monitor needs to watch conditions and execute
5. **Idempotency** - Prevent duplicate executions across restarts

## 🔄 **Corrected Data Flow**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingest        │    │   Learning       │    │   Decision       │    │   Position       │
│   Social        │───▶│   System        │───▶│   Maker         │───▶│   Creation       │
│   Signals       │    │   (Scoring)     │    │   (DM)          │    │   (DB)           │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Social Strands  │    │ Curator Scores  │    │ Allocation %    │    │ Position Record │
│ Token Data      │    │ Intent Analysis │    │ (4-15%)         │    │ Features Init    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Price         │    │   TA Tracker    │    │   Uptrend        │    │   PM Core        │
│   Monitor       │───▶│   (Enhanced)    │───▶│   Engine        │───▶│   (Enhanced)     │
│   (Real-time)   │    │   (5min)        │    │   (5min)        │    │   (1h + Events) │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Price Changes   │    │ RSI/EMA/ATR     │    │ S0-S5 States    │    │ A/E Levers       │
│ TA Signals      │    │ ADX/VO_z        │    │ Setup A/B/C     │    │ Execution        │
│ Breakouts       │    │ Compression     │    │ R/R Ratios      │    │ Conditions       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                                              │
                                                                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Execution      │    │   Position       │    │   Strands       │    │   Monitoring     │
│   Engine         │◀───│   Updates        │◀───│   (AD_strands)  │◀───│   & Analytics   │
│   (Native)       │    │   (DB)           │    │   (Logging)     │    │   (Performance) │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 **Implementation Plan**

### **Phase 1: Learning System → PM Trigger**

**Problem**: DM creates positions, but PM doesn't know about them
**Solution**: Learning System triggers PM when new positions are created

```python
# In UniversalLearningSystem._trigger_decision_maker()
async def _trigger_decision_maker(self, strand: Dict[str, Any]) -> None:
    # ... existing DM logic ...
    
    # NEW: If DM approves, trigger PM to start monitoring
    if decision_result.get('decision') == 'approve':
        await self._trigger_pm_monitoring(strand)

async def _trigger_pm_monitoring(self, strand: Dict[str, Any]) -> None:
    """Trigger PM to start monitoring a new position"""
    try:
        # Emit event for PM to pick up new position
        from intelligence.lowcap_portfolio_manager.events.bus import emit
        emit("new_position_created", {
            "position_id": strand.get('content', {}).get('position_id'),
            "token_contract": strand.get('content', {}).get('token', {}).get('contract'),
            "token_chain": strand.get('content', {}).get('token', {}).get('chain'),
            "allocation_pct": strand.get('content', {}).get('allocation_pct'),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        self.logger.error(f"Failed to trigger PM monitoring: {e}")
```

### **Phase 2: Price Monitoring Integration**

**Problem**: PM runs on schedule, not on price changes
**Solution**: Price monitor triggers PM decisions on significant changes

```python
# Enhanced price monitoring in PositionMonitor
class PositionMonitor:
    async def _monitoring_loop(self, check_interval: int = 30):
        """Monitor positions and trigger PM on significant changes"""
        while self.monitoring:
            try:
                # Get active positions
                positions = await self._get_active_positions()
                
                for position in positions:
                    # Check for significant price/TA changes
                    significant_change = await self._detect_significant_change(position)
                    
                    if significant_change:
                        # Trigger PM decision
                        await self._trigger_pm_decision(position, significant_change)
                        
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(check_interval)
    
    async def _detect_significant_change(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect significant price/TA changes that should trigger PM decisions"""
        features = position.get('features', {})
        ta = features.get('ta', {})
        geometry = features.get('geometry', {})
        
        # Check for breakout conditions
        if geometry.get('sr_break') in ['bull', 'bear']:
            return {
                'type': 'structure_break',
                'direction': geometry.get('sr_break'),
                'confidence': geometry.get('sr_conf', 0.0)
            }
        
        # Check for diagonal breaks
        if geometry.get('diag_break') in ['bull', 'bear']:
            return {
                'type': 'diagonal_break', 
                'direction': geometry.get('diag_break'),
                'confidence': geometry.get('diag_conf', 0.0)
            }
        
        # Check for TA signals
        if ta.get('rsi', {}).get('divergence') in ['bull', 'bear']:
            return {
                'type': 'rsi_divergence',
                'direction': ta.get('rsi', {}).get('divergence')
            }
        
        return None
    
    async def _trigger_pm_decision(self, position: Dict[str, Any], change: Dict[str, Any]) -> None:
        """Trigger PM to make a decision based on significant change"""
        try:
            from intelligence.lowcap_portfolio_manager.events.bus import emit
            emit("significant_price_change", {
                "position_id": position['id'],
                "token_contract": position['token_contract'],
                "change_type": change['type'],
                "change_data": change,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to trigger PM decision: {e}")
```

### **Phase 3: PM → Execution Conditions**

**Problem**: PM makes decisions but doesn't output specific execution conditions
**Solution**: PM outputs execution conditions to database, Price Monitor watches and executes

#### **3.1: PM Execution Conditions Output**

```python
# In PMCoreTick.run()
def run(self) -> int:
    # ... existing A/E computation ...
    
    for position in positions:
        actions = plan_actions(position, a_final, e_final, phase)
        
        for action in actions:
            if action['decision_type'] != 'hold':
                # Create execution condition
                self._create_execution_condition(position, action, a_final, e_final)

def _create_execution_condition(self, position: Dict[str, Any], action: Dict[str, Any], 
                               a_final: float, e_final: float) -> None:
    """Create execution condition for Price Monitor to watch"""
    try:
        # Calculate exact native amounts
        amount_sol = self._calculate_exact_amount(position, action)
        
        # Determine execution condition based on action type
        condition = self._build_execution_condition(position, action)
        
        # Store in pm_action_queue
        self.sb.table("pm_action_queue").insert({
            "position_id": position['id'],
            "action_id": str(uuid.uuid4()),
            "action_type": action['decision_type'],
            "condition": condition,
            "execution": {
                "amount_sol": amount_sol,
                "max_slippage_bps": 50,
                "priority": "normal"
            },
            "safety": {
                "forbid_if_euphoria": action.get('forbid_if_euphoria', False),
                "forbid_if_emergency_exit": action.get('forbid_if_emergency_exit', False)
            },
            "correlation_id": str(uuid.uuid4()),
            "a_value": a_final,
            "e_value": e_final,
            "status": "pending",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        }).execute()
        
    except Exception as e:
        logger.error(f"Failed to create execution condition: {e}")

def _build_execution_condition(self, position: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    """Build specific execution condition based on action type"""
    decision_type = action['decision_type']
    features = position.get('features', {})
    geometry = features.get('geometry', {})
    ta = features.get('ta', {})
    
    if decision_type in ['add', 'trend_add']:
        # Entry conditions
        if geometry.get('sr_break') == 'bull':
            return {
                "trigger": "horizontal_touch",
                "level_native": geometry.get('sr_level', 0.0),
                "halo_native": geometry.get('sr_halo', 0.0),
                "direction": "near_touch"
            }
        elif geometry.get('diag_break') == 'bull':
            return {
                "trigger": "diagonal_touch", 
                "level_native": geometry.get('diag_level', 0.0),
                "halo_native": geometry.get('diag_halo', 0.0),
                "direction": "near_touch",
                "diagonal_type": "upper"
            }
        elif ta.get('ema20') and ta.get('ema50'):
            return {
                "trigger": "ema_touch",
                "level_native": ta.get('ema20', 0.0),
                "halo_native": ta.get('atr', 0.0) * 0.5,
                "direction": "near_touch",
                "ema_type": "EMA20"
            }
    
    elif decision_type in ['trim', 'trail', 'full_exit']:
        # Exit conditions
        if action.get('trigger') == 'euphoria':
            return {
                "trigger": "euphoria_exit",
                "level_native": ta.get('ema20', 0.0),
                "halo_native": ta.get('atr', 0.0) * 0.3,
                "direction": "above",
                "euphoria_threshold": 0.70
            }
        elif action.get('trigger') == 'emergency':
            return {
                "trigger": "emergency_exit",
                "level_native": ta.get('ema50', 0.0),
                "halo_native": 0.0,
                "direction": "below",
                "urgency": "high"
            }
    
    return {}

def _calculate_exact_amount(self, position: Dict[str, Any], action: Dict[str, Any]) -> float:
    """Calculate exact SOL amount for execution"""
    decision_type = action['decision_type']
    size_frac = action.get('size_frac', 0.0)
    
    if decision_type in ['add', 'trend_add']:
        # Calculate SOL amount to spend
        allocation_usd = float(position.get('total_allocation_usd', 0.0))
        sol_price = self._get_sol_price()
        if sol_price and allocation_usd > 0:
            return (allocation_usd * size_frac) / sol_price
    
    elif decision_type in ['trim', 'trail', 'full_exit']:
        # Calculate SOL amount to receive
        total_quantity = float(position.get('total_quantity', 0.0))
        current_price = self._get_current_price(position)
        if current_price and total_quantity > 0:
            return (total_quantity * size_frac * current_price) / self._get_sol_price()
    
    return 0.0
```

#### **3.2: Price Monitor Execution**

```python
# Enhanced Price Monitor for execution
class PositionMonitor:
    async def _monitoring_loop(self, check_interval: int = 30):
        """Monitor positions and execute when conditions are met"""
        while self.monitoring:
            try:
                # Get pending execution conditions
                pending_actions = await self._get_pending_actions()
                
                for action in pending_actions:
                    # Check if condition is met
                    condition_met = await self._check_execution_condition(action)
                    
                    if condition_met:
                        # Execute the action
                        await self._execute_action(action)
                        
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(check_interval)
    
    async def _get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get pending actions from pm_action_queue"""
        try:
            result = self.sb.table("pm_action_queue").select("*").eq("status", "pending").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get pending actions: {e}")
            return []
    
    async def _check_execution_condition(self, action: Dict[str, Any]) -> bool:
        """Check if execution condition is met"""
        try:
            condition = action['condition']
            trigger = condition.get('trigger')
            level_native = condition.get('level_native', 0.0)
            halo_native = condition.get('halo_native', 0.0)
            direction = condition.get('direction', 'near_touch')
            
            # Get current price
            current_price = await self._get_current_price(action['token_contract'], action['token_chain'])
            if not current_price:
                return False
            
            # Check condition based on trigger type
            if trigger == 'horizontal_touch':
                return self._check_horizontal_touch(current_price, level_native, halo_native, direction)
            elif trigger == 'diagonal_touch':
                return self._check_diagonal_touch(current_price, level_native, halo_native, direction)
            elif trigger == 'ema_touch':
                return self._check_ema_touch(current_price, level_native, halo_native, direction)
            elif trigger == 'euphoria_exit':
                return self._check_euphoria_exit(current_price, level_native, halo_native, direction)
            elif trigger == 'emergency_exit':
                return self._check_emergency_exit(current_price, level_native, halo_native, direction)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check execution condition: {e}")
            return False
    
    def _check_horizontal_touch(self, current_price: float, level: float, halo: float, direction: str) -> bool:
        """Check if price touches horizontal level within halo"""
        if direction == 'near_touch':
            return abs(current_price - level) <= halo
        elif direction == 'above':
            return current_price > level - halo
        elif direction == 'below':
            return current_price < level + halo
        return False
    
    def _check_diagonal_touch(self, current_price: float, level: float, halo: float, direction: str) -> bool:
        """Check if price touches diagonal level within halo"""
        # Similar logic to horizontal but could include slope calculations
        return self._check_horizontal_touch(current_price, level, halo, direction)
    
    def _check_ema_touch(self, current_price: float, level: float, halo: float, direction: str) -> bool:
        """Check if price touches EMA level within halo"""
        return self._check_horizontal_touch(current_price, level, halo, direction)
    
    def _check_euphoria_exit(self, current_price: float, level: float, halo: float, direction: str) -> bool:
        """Check if euphoria exit condition is met"""
        # Could include additional logic like euphoria curve threshold
        return self._check_horizontal_touch(current_price, level, halo, direction)
    
    def _check_emergency_exit(self, current_price: float, level: float, halo: float, direction: str) -> bool:
        """Check if emergency exit condition is met"""
        return self._check_horizontal_touch(current_price, level, halo, direction)
    
    async def _execute_action(self, action: Dict[str, Any]) -> None:
        """Execute the action when condition is met"""
        try:
            # Idempotency check
            correlation_id = action['correlation_id']
            if not await self._idem_allow(correlation_id):
                return
            
            # Execute trade
            execution_result = await self._execute_trade(action)
            
            if execution_result['success']:
                # Update action status
                await self._update_action_status(action['action_id'], 'executed', execution_result)
                
                # Update position record
                await self._update_position_record(action, execution_result)
                
                # Create execution strand
                await self._create_execution_strand(action, execution_result)
            else:
                # Mark as failed
                await self._update_action_status(action['action_id'], 'failed', execution_result)
                
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            await self._update_action_status(action['action_id'], 'failed', {'error': str(e)})
    
    async def _execute_trade(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual trade"""
        try:
            action_type = action['action_type']
            token_contract = action['token_contract']
            token_chain = action['token_chain']
            amount_sol = action['execution']['amount_sol']
            
            # Get current price
            current_price = await self._get_current_price(token_contract, token_chain)
            
            if action_type in ['add', 'trend_add']:
                # Execute buy
                result = await self._execute_buy(token_contract, token_chain, amount_sol, current_price)
            elif action_type in ['trim', 'trail', 'full_exit']:
                # Execute sell
                result = await self._execute_sell(token_contract, token_chain, amount_sol, current_price)
            else:
                return {'success': False, 'error': 'Unknown action type'}
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {'success': False, 'error': str(e)}
```

### **Phase 4: Database Schema & Idempotency**

**Problem**: Need database schema for execution conditions and idempotency
**Solution**: Create `pm_action_queue` table with built-in idempotency

```sql
-- Create PM action queue table
CREATE TABLE pm_action_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    action_id UUID NOT NULL,
    action_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'trim'
    condition JSONB NOT NULL,
    execution JSONB NOT NULL,
    safety JSONB NOT NULL,
    correlation_id UUID NOT NULL,
    a_value DECIMAL(3,2) NOT NULL,
    e_value DECIMAL(3,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'executed', 'expired', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP NULL,
    executed_price_native DECIMAL(20,8) NULL,
    executed_amount_sol DECIMAL(10,4) NULL,
    tx_hash TEXT NULL,
    error_message TEXT NULL
);

CREATE INDEX idx_pm_action_queue_position ON pm_action_queue(position_id);
CREATE INDEX idx_pm_action_queue_status ON pm_action_queue(status);
CREATE INDEX idx_pm_action_queue_correlation ON pm_action_queue(correlation_id);
CREATE INDEX idx_pm_action_queue_expires ON pm_action_queue(expires_at);
CREATE UNIQUE INDEX idx_pm_action_queue_correlation_unique ON pm_action_queue(correlation_id);
```

```python
# Enhanced idempotency with correlation_id uniqueness
async def _idem_allow(self, correlation_id: str) -> bool:
    """Check if execution is allowed using correlation_id uniqueness"""
    try:
        # Check if correlation_id already exists
        result = self.sb.table("pm_action_queue").select("id").eq("correlation_id", correlation_id).execute()
        return len(result.data) == 0
        
    except Exception as e:
        logger.error(f"Failed to check idempotency: {e}")
        return False

async def _update_action_status(self, action_id: str, status: str, execution_result: Dict[str, Any]) -> None:
    """Update action status in database"""
    try:
        update_data = {
            "status": status,
            "executed_at": datetime.now(timezone.utc).isoformat() if status == "executed" else None
        }
        
        if status == "executed" and execution_result.get('success'):
            update_data.update({
                "executed_price_native": execution_result.get('price', 0.0),
                "executed_amount_sol": execution_result.get('amount_sol', 0.0),
                "tx_hash": execution_result.get('tx_hash', '')
            })
        elif status == "failed":
            update_data["error_message"] = execution_result.get('error', 'Unknown error')
        
        self.sb.table("pm_action_queue").update(update_data).eq("action_id", action_id).execute()
        
    except Exception as e:
        logger.error(f"Failed to update action status: {e}")
```

### **Phase 5: Position Updates & Strands**

**Problem**: Executions need to update position records and create audit trails
**Solution**: Update positions and create execution strands after successful execution

```python
# Enhanced execution with position updates and strands
async def _update_position_record(self, action: Dict[str, Any], execution_result: Dict[str, Any]) -> None:
    """Update position record with execution details"""
    try:
        position_id = action['position_id']
        action_type = action['action_type']
        amount_sol = execution_result.get('amount_sol', 0.0)
        price_native = execution_result.get('price', 0.0)
        tx_hash = execution_result.get('tx_hash', '')
        
        if action_type in ['add', 'trend_add']:
            # Add to entries
            entry = {
                "price": price_native,
                "quantity": amount_sol / price_native if price_native > 0 else 0,
                "usd": amount_sol * self._get_sol_price(),
                "venue": execution_result.get('venue', 'unknown'),
                "tx": tx_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": action_type
            }
            
            # Update position
            self.sb.table("lowcap_positions").update({
                "total_quantity": self.sb.table("lowcap_positions").select("total_quantity").eq("id", position_id).execute().data[0]['total_quantity'] + (amount_sol / price_native if price_native > 0 else 0),
                "total_investment_native": self.sb.table("lowcap_positions").select("total_investment_native").eq("id", position_id).execute().data[0]['total_investment_native'] + amount_sol,
                "entries": self.sb.table("lowcap_positions").select("entries").eq("id", position_id).execute().data[0]['entries'] + [entry]
            }).eq("id", position_id).execute()
        
        elif action_type in ['trim', 'trail', 'full_exit']:
            # Add to exits
            exit_record = {
                "price": price_native,
                "quantity": amount_sol / price_native if price_native > 0 else 0,
                "usd": amount_sol * self._get_sol_price(),
                "venue": execution_result.get('venue', 'unknown'),
                "tx": tx_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": action_type
            }
            
            # Update position
            self.sb.table("lowcap_positions").update({
                "total_quantity": self.sb.table("lowcap_positions").select("total_quantity").eq("id", position_id).execute().data[0]['total_quantity'] - (amount_sol / price_native if price_native > 0 else 0),
                "total_extracted_native": self.sb.table("lowcap_positions").select("total_extracted_native").eq("id", position_id).execute().data[0]['total_extracted_native'] + amount_sol,
                "exits": self.sb.table("lowcap_positions").select("exits").eq("id", position_id).execute().data[0]['exits'] + [exit_record]
            }).eq("id", position_id).execute()
            
    except Exception as e:
        logger.error(f"Failed to update position record: {e}")

async def _create_execution_strand(self, action: Dict[str, Any], execution_result: Dict[str, Any]) -> None:
    """Create execution strand for audit trail"""
    try:
        strand = {
            "kind": "pm_execution",
            "module": "portfolio_manager",
            "content": {
                "position_id": action['position_id'],
                "token_contract": action['token_contract'],
                "token_chain": action['token_chain'],
                "action_type": action['action_type'],
                "amount_sol": execution_result.get('amount_sol', 0.0),
                "execution_result": execution_result,
                "a_value": action['a_value'],
                "e_value": action['e_value'],
                "condition": action['condition'],
                "correlation_id": action['correlation_id']
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.sb.table("ad_strands").insert(strand).execute()
        
    except Exception as e:
        logger.error(f"Failed to create execution strand: {e}")
```

## 🎯 **Key Integration Points**

### **1. Learning System Changes**
- **Keep Learning System intact** - only add PM trigger for approved decisions
- **Don't break existing flows** - DM → Trader path remains for other strand types
- **Add PM monitoring trigger** when `decision_lowcap` strands are approved

### **2. Price Monitoring Integration**
- **Real-time price monitoring** triggers PM decisions on significant changes
- **Structure breaks, diagonal breaks, TA signals** all trigger PM evaluation
- **PM Core runs on schedule** + **event-driven** for responsiveness

### **3. PM → Execution Conditions**
- **PM outputs specific execution conditions** to `pm_action_queue` table
- **Exact SOL amounts** and **precise trigger conditions** (horizontal, diagonal, EMA, emergency)
- **Safety guards** (forbid if euphoria, forbid if emergency exit)
- **24-hour expiration** for conditions

### **4. Price Monitor → Execution**
- **Price Monitor watches `pm_action_queue`** for pending conditions
- **Real-time condition checking** (horizontal touch, diagonal touch, EMA touch, etc.)
- **Idempotent execution** using correlation_id uniqueness
- **Position updates** and **execution strands** for audit trail

### **5. Database Schema**
- **Use existing `lowcap_positions_schema.sql`**
- **Add `pm_action_queue` table** for execution conditions
- **Extend `features` JSONB** for PM data (already exists)
- **Built-in idempotency** with correlation_id uniqueness

## 🚀 **Implementation Order**

1. **Phase 1**: Learning System → PM trigger (new position monitoring)
2. **Phase 2**: Price monitoring → PM decisions (significant changes)
3. **Phase 3**: PM → Execution conditions (specific conditions to database)
4. **Phase 4**: Database schema & idempotency (`pm_action_queue` table)
5. **Phase 5**: Position updates & strands (audit trail)

## 🔍 **Testing Strategy**

1. **Unit tests** for each component
2. **Integration tests** for event flows
3. **End-to-end tests** with mock executors
4. **Production testing** with canary symbols
5. **Performance monitoring** for latency and resource usage

---

*This architecture ensures PM is properly integrated with the existing system while maintaining clean separation of concerns and robust execution guarantees. The PM outputs specific execution conditions, the Price Monitor watches and executes them, and the system maintains full audit trails.*
