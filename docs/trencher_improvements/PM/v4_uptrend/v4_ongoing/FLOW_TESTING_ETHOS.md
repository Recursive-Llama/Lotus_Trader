# Flow Testing Ethos

**Purpose**: Define the testing philosophy for this system - follow packets through, don't build test infrastructure.

---

## Core Principle

**Turn the system on. Inject a packet. Query the database. That's it.**

The system runs itself (scheduled jobs, event processing, etc.). The test just observes.

---

## What Flow Testing IS

### 1. Turn the System On
- **Start the actual system** (scheduled jobs, event processing, etc.)
- System runs like it does in production
- Test doesn't orchestrate - system orchestrates itself
- Test just observes what happens

### 2. Inject Real Data at Ingress
- Create one real social signal (or use existing one)
- Minimal setup - just what's needed to get a packet into the system
- Use real tokens, real curators (from your actual data)
- **Then let the system process it** (don't call functions directly)

### 3. Follow the Packet Using Database Queries
- Use existing IDs to trace the path: `signal_id` → `decision_id` → `position_id` → `strand_id`
- Query the database at each step: "Does the decision exist? Do positions exist?"
- Follow the actual data flow through the real system
- **System processes it, test just queries to see what happened**

### 4. Know Exactly Where It Dies
- If packet dies at step 5, query shows: decision exists, positions exist, but no execution
- Not "test failed" - "packet `signal_001` died at step 5 (PM execution)"
- Database state tells you exactly what happened

### 5. Mock ONLY What You Must
- **Mock Uptrend Engine signals** (because we can't wait days/weeks for real market conditions)
- **Mock A/E scores** (to test different combinations)
- **Everything else is real**: Real database, real learning system, real PM, real execution
- **System runs itself** - scheduled jobs, event processing, etc.

### 6. Test the Path, Not Just Outcomes
- Don't just check "did it work?"
- Check "can I query each step in the path?"
- Verify the packet traveled through: signal → decision → positions → execution → closure → learning
- **System did the work, test just verified it happened**

---

## What Flow Testing IS NOT

### ❌ NOT Traditional Unit Testing
- Don't create test fixtures
- Don't mock the entire system
- Don't build test infrastructure
- Don't isolate components

### ❌ NOT Complex Setup
- Don't create test databases with complex schemas
- Don't seed lots of test data
- Don't create test helpers/fixtures
- Don't build test frameworks

### ❌ NOT Orchestrating the System
- Don't call `decision_maker.make_decision()` directly
- Don't call `pm_core_tick.run()` directly
- Don't orchestrate the system - let it run itself
- The system has scheduled jobs, event processing, etc. - use them

### ❌ NOT Outcome-Only Testing
- Don't just check "did coefficients update?"
- Check "can I query the path: signal → decision → positions → closure → learning?"
- Verify each step exists and is queryable

### ❌ NOT Mocking Everything
- Don't mock the learning system
- Don't mock the database
- Don't mock PM execution (use real execution with small amounts)
- Only mock what you must (Uptrend Engine signals)

---

## Example: Correct Flow Test Structure

```python
def test_complete_learning_loop():
    """
    Follow one signal through the entire system.
    System runs itself. Test just observes.
    """
    
    # Step 0: Turn the system on (or it's already running)
    # - Scheduled jobs running (decision_maker, pm_core_tick, etc.)
    # - Event processing active
    # - System orchestrates itself
    
    # Step 1: Inject one signal (minimal setup)
    signal_id = create_social_signal(token="POLYTALE", curator="0xdetweiler")
    # System processes it automatically (scheduled job picks it up)
    
    # Step 2: Wait a bit, then query - does decision exist?
    time.sleep(5)  # Let system process
    decision = query("SELECT * FROM ad_strands WHERE kind='decision_lowcap' AND parent_id=?", signal_id)
    assert decision, "Packet died at step 2: No decision created (system didn't process signal)"
    decision_id = decision['id']
    
    # Step 3: Query - do positions exist? (system created them automatically)
    positions = query("SELECT * FROM lowcap_positions WHERE token_contract=? AND created_at > ?", 
                     token_contract, signal_time)
    assert len(positions) == 4, f"Packet died at step 3: Expected 4 positions, got {len(positions)}"
    position_id = positions[0]['id']  # Use 1h position
    
    # Step 4: Mock Uptrend Engine (ONLY thing we mock) + set A/E
    mock_engine_signal(position_id, state="S1", buy_signal=True)
    set_a_e_scores(position_id, a_final=0.6, e_final=0.3)
    # System will process this on next PM tick (scheduled job)
    
    # Step 5: Wait for PM tick to run (scheduled job), then query - did buy execute?
    time.sleep(60)  # Wait for next PM tick (or trigger it if needed)
    position = query("SELECT * FROM lowcap_positions WHERE id=?", position_id)
    exec_history = position['features']['pm_execution_history']
    assert exec_history.get('last_s1_buy'), "Packet died at step 5: Buy did not execute (PM didn't process)"
    assert position['total_quantity'] > 0, "Packet died at step 5: No tokens purchased"
    
    # Step 6: Mock Uptrend Engine again (trim signal)
    mock_engine_signal(position_id, state="S3", trim_flag=True)
    set_a_e_scores(position_id, a_final=0.4, e_final=0.7)
    
    # Step 7: Wait for PM tick, then query - did trim execute?
    time.sleep(60)  # Wait for next PM tick
    position = query("SELECT * FROM lowcap_positions WHERE id=?", position_id)
    exec_history = position['features']['pm_execution_history']
    assert exec_history.get('last_trim'), "Packet died at step 7: Trim did not execute"
    
    # Step 8: Mock Uptrend Engine again (emergency exit)
    mock_engine_signal(position_id, state="S3", emergency_exit=True)
    
    # Step 9: Wait for PM tick, then query - is position closed?
    time.sleep(60)  # Wait for next PM tick
    position = query("SELECT * FROM lowcap_positions WHERE id=?", position_id)
    assert position['status'] == 'watchlist', "Packet died at step 9: Position not closed"
    assert position['total_quantity'] == 0, "Packet died at step 9: Position still has tokens"
    assert position['completed_trades'], "Packet died at step 9: No completed_trades"
    
    # Step 10: Query - does position_closed strand exist? (system created it automatically)
    strand = query("SELECT * FROM ad_strands WHERE kind='position_closed' AND position_id=?", position_id)
    assert strand, "Packet died at step 10: No position_closed strand (PM didn't create it)"
    
    # Step 11: Query - are coefficients updated? (system processed it automatically)
    time.sleep(5)  # Let learning system process
    coefficient = query("""
        SELECT * FROM learning_coefficients 
        WHERE module='dm' AND scope='lever' AND name='curator' AND key='0xdetweiler'
    """)
    assert coefficient, "Packet died at step 11: Coefficients not updated (learning system didn't process)"
    assert coefficient['n'] == 1, "Packet died at step 11: Coefficient count wrong"
    
    # Step 12: Query - are braids created? (system processed it automatically)
    braids = query("SELECT * FROM learning_braids WHERE module='dm' LIMIT 1")
    assert braids, "Packet died at step 12: No braids created"
    
    # SUCCESS: Packet reached all sinks
    print(f"✅ Packet {signal_id} successfully traveled: signal → decision → positions → buy → trim → exit → learning")
    print(f"   System processed everything automatically - test just observed")
```

**Key Points**:
- ~100-200 lines of code
- Mostly database queries
- One signal injection
- Mock ONLY Uptrend Engine (because timing)
- Everything else is real system
- Clear failure points: "Packet died at step X"

---

## Example: WRONG Flow Test Structure

```python
# ❌ WRONG: Too much setup, too much mocking, too much infrastructure

@pytest.fixture
def test_database():
    """Create test database with complex schema"""
    # ... 50 lines of setup ...

@pytest.fixture
def test_token():
    """Create test token fixture"""
    # ... 20 lines ...

@pytest.fixture
def mock_learning_system():
    """Mock the entire learning system"""
    # ... 30 lines ...

@pytest.fixture
def mock_pm_executor():
    """Mock PM executor"""
    # ... 30 lines ...

def test_complete_learning_loop(test_database, test_token, mock_learning_system, mock_pm_executor):
    """Complex test with lots of mocks"""
    # ... 500 lines of test code ...
    # Tests outcomes, not path
    # Can't follow packet through
    # Too much infrastructure
```

**Why This Is Wrong**:
- Too much setup (fixtures, mocks, infrastructure)
- Mocks the system instead of testing it
- Can't follow packet through (everything is mocked)
- Tests outcomes, not path
- Complex, hard to understand
- **Orchestrates the system** instead of letting it run itself

---

## The Flow Test Checklist

Before writing a flow test, ask:

1. **Is the system running itself?**
   - ✅ System has scheduled jobs, event processing → Good
   - ❌ Test calls functions directly → Bad

2. **Am I just observing, not orchestrating?**
   - ✅ Inject packet, query database → Good
   - ❌ Call decision_maker.make_decision(), pm_core_tick.run() → Bad

3. **Can I follow one packet through using database queries?**
   - ✅ Yes → Good flow test
   - ❌ No → Redesign

4. **Am I mocking only what I must?**
   - ✅ Only Uptrend Engine → Good
   - ❌ Mocking learning system, database, PM → Bad

5. **Can I query each step in the path?**
   - ✅ Yes → Good flow test
   - ❌ No → Redesign

6. **Do I know exactly where it dies if it dies?**
   - ✅ "Packet died at step 5" → Good
   - ❌ "Test failed" → Bad

7. **Is the test simple and direct?**
   - ✅ ~100-200 lines, mostly queries → Good
   - ❌ 500+ lines, lots of infrastructure → Bad

---

## Flow Test Template

```python
def test_[scenario_name]():
    """
    Follow one packet through: [ingress] → [step1] → [step2] → ... → [sink]
    """
    
    # Step 1: Inject packet at ingress
    packet_id = inject_packet(...)
    
    # Step 2: Query - does step1 exist?
    step1 = query("SELECT * FROM table WHERE id=?", packet_id)
    assert step1, f"Packet {packet_id} died at step 2: No step1"
    
    # Step 3: Query - does step2 exist?
    step2 = query("SELECT * FROM table WHERE parent_id=?", step1['id'])
    assert step2, f"Packet {packet_id} died at step 3: No step2"
    
    # ... continue following the path ...
    
    # Final: Query - did packet reach sink?
    sink = query("SELECT * FROM table WHERE ...")
    assert sink, f"Packet {packet_id} died at final step: No sink"
    
    print(f"✅ Packet {packet_id} successfully traveled: ingress → step1 → step2 → ... → sink")
```

---

## Why This Matters

**Traditional Testing**:
- Tests components in isolation
- Mocks everything
- Can't see the full path
- "Test passed" but system doesn't work

**Flow Testing**:
- Tests the actual system
- Follows real packets through
- Can see exactly where it breaks
- "Packet reached sink" = system works

**If you can't follow a packet through, the system is missing a link. Add it.**

---

## Summary

**Flow Testing = Turn the system on. Inject a packet. Query the database. That's it.**

- ✅ **System runs itself** (scheduled jobs, event processing)
- ✅ **Test just observes** (inject packet, query database)
- ✅ Simple, direct, query-based
- ✅ Mock ONLY what you must (Uptrend Engine)
- ✅ Test the path, not just outcomes
- ✅ Know exactly where it dies

- ❌ No orchestrating the system (don't call functions directly)
- ❌ No complex setup
- ❌ No test infrastructure
- ❌ No mocking the system
- ❌ No traditional unit testing approach

**Turn it on. Inject a packet. Query the database. The system does the work.**

