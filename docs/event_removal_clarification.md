# Event Removal Clarification

**Question**: Are we just removing the event subscription code, or also the unneeded stuff in it (event emissions)?

---

## What We're Removing

### 1. Event Subscriptions (pm_core_tick.py)

**Remove**:
- `_subscribe_events()` function (lines 2954-2990)
- Call to `_subscribe_events()` in `main()` (line 3002)

**Why**: These subscriptions are broken and causing excessive PM Core Tick runs

---

### 2. Event Emissions (Optional - Cleanup)

**Current State**:

| Event | Emitted By | Subscribed By | Status |
|-------|------------|---------------|--------|
| `phase_transition` | `tracker.py` (line 266)<br>`spiral/persist.py` (line 48) | `pm_core_tick.py` only | ✅ Emitted, but we're removing subscriber |
| `structure_change` | **Never emitted** | `pm_core_tick.py` only | ❌ Dead code |
| `sr_break_detected` | **Never emitted** | `pm_core_tick.py` only | ❌ Dead code |
| `ema_trail_breach` | **Never emitted** | `pm_core_tick.py` only | ❌ Dead code |

**Recommendation**:

#### Remove Emissions (Cleanup)

**tracker.py** (line 266):
```python
# Remove this:
bus.emit("phase_transition", {...})
```

**spiral/persist.py** (line 48):
```python
# Remove this:
emit("phase_transition", {...})
```

**Why**:
- No one subscribes to these events anymore (we removed the only subscriber)
- They're just wasting computation
- Cleaner code

#### Keep Event Bus Infrastructure

**Keep**: `src/intelligence/lowcap_portfolio_manager/events/bus.py`

**Why**:
- Might be used elsewhere in the future
- Removing it could break other code
- It's just infrastructure (not the problem)

---

## Summary

### What We're Removing

1. ✅ **Subscription code** (`_subscribe_events()` in `pm_core_tick.py`)
   - **Required** - This is the broken code causing excessive runs

2. ✅ **Event emissions** (`phase_transition` in `tracker.py` and `spiral/persist.py`)
   - **Recommended** - Cleanup since no one subscribes anymore
   - **Optional** - System works without this, but cleaner to remove

3. ❌ **Event bus infrastructure** (`events/bus.py`)
   - **Keep** - Might be used elsewhere, just infrastructure

### What We're NOT Removing

- Event bus system itself (`events/bus.py`) - Keep for potential future use
- Other event types that might be used elsewhere

---

## Implementation

### Required Changes

1. **pm_core_tick.py**:
   - Remove `_subscribe_events()` function
   - Remove call to `_subscribe_events()` in `main()`

### Optional Cleanup (Recommended)

2. **tracker.py** (line 266):
   - Remove `bus.emit("phase_transition", {...})`

3. **spiral/persist.py** (line 48):
   - Remove `emit("phase_transition", {...})`

---

## Answer to Your Question

**We're removing**:
1. ✅ The subscription code (required - fixes the bug)
2. ✅ The event emissions (optional cleanup - no one listening anyway)

**We're keeping**:
- The event bus infrastructure (might be used elsewhere)

**The "unneeded stuff"** = the event emissions that no one subscribes to anymore. Good catch - we should remove those too for cleaner code!

---

**End of Clarification**

