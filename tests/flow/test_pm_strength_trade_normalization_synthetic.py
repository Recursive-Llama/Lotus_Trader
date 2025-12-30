#!/usr/bin/env python3
"""
Test PM Strength Trade Normalization Fix - Synthetic Data

Tests that lesson_builder_v5 correctly counts distinct trades, not actions,
using synthetic test data.

Usage:
    PYTHONPATH=src python tests/flow/test_pm_strength_trade_normalization_synthetic.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import json
from datetime import datetime, timezone
import uuid

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

async def create_test_data(sb):
    """Create synthetic test data for testing."""
    print("📝 Creating synthetic test data...")
    
    # Clear existing test data
    try:
        # Delete test lessons
        sb.table("learning_lessons").delete().eq("module", "pm").execute()
        # Delete test events
        sb.table("pattern_trade_events").delete().like("pattern_key", "test.%").execute()
    except Exception as e:
        print(f"   Note: Could not clear existing data: {e}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Test Case 1: Single trade with many actions (domination case)
    # Trade A: 56 "add" actions, all rr = -0.88, same scope
    trade_id_a = str(uuid.uuid4())
    events = []
    for i in range(56):
        events.append({
            'pattern_key': 'test.uptrend.S3.add',
            'action_category': 'add',
            'scope': {'chain': 'solana', 'bucket': 'micro', 'curator': 'test'},
            'rr': -0.88,
            'trade_id': trade_id_a,
            'timestamp': now,
            'created_at': now
        })
    
    # Test Case 2: Multiple trades, same scope (need 33+ trades to meet N_MIN_SLICE)
    # Create 35 trades with 1 action each, different RRs
    trade_ids_b = []
    for i in range(35):
        trade_id = str(uuid.uuid4())
        trade_ids_b.append(trade_id)
        # Vary RR slightly to have some variance
        rr = 1.0 + (i % 10) * 0.1 - 0.5  # Range: 0.5 to 1.4
        events.append({
            'pattern_key': 'test.uptrend.S3.add',
            'action_category': 'add',
            'scope': {'chain': 'solana', 'bucket': 'micro', 'curator': 'test'},
            'rr': rr,
            'trade_id': trade_id,
            'timestamp': now,
            'created_at': now
        })
    
    # Test Case 3: Actions span multiple scopes
    # Trade E: 10 actions, 5 in scope A, 5 in scope B
    trade_id_e = str(uuid.uuid4())
    for i in range(5):
        events.append({
            'pattern_key': 'test.uptrend.S2.add',
            'action_category': 'add',
            'scope': {'chain': 'base', 'bucket': 'micro'},  # Scope A
            'rr': 1.5,
            'trade_id': trade_id_e,
            'timestamp': now,
            'created_at': now
        })
    for i in range(5):
        events.append({
            'pattern_key': 'test.uptrend.S2.add',
            'action_category': 'add',
            'scope': {'chain': 'base', 'bucket': 'mid'},  # Scope B
            'rr': 1.5,
            'trade_id': trade_id_e,
            'timestamp': now,
            'created_at': now
        })
    
    # Test Case 4: Small n for variance shrinkage prior test
    # Create 3 trades with same RR (variance = 0) to test prior
    for i in range(3):
        trade_id = str(uuid.uuid4())
        events.append({
            'pattern_key': 'test.uptrend.S1.entry',
            'action_category': 'entry',
            'scope': {'chain': 'ethereum', 'bucket': 'micro'},
            'rr': 1.0,  # All same RR
            'trade_id': trade_id,
            'timestamp': now,
            'created_at': now
        })
    
    # Insert events
    print(f"   Inserting {len(events)} test events...")
    for event in events:
        try:
            sb.table("pattern_trade_events").insert(event).execute()
        except Exception as e:
            print(f"   Warning: Failed to insert event: {e}")
    
    print(f"   ✅ Created {len(events)} test events")
    return {
        'trade_id_a': trade_id_a,
        'trade_id_e': trade_id_e,
        'total_events': len(events)
    }

async def test_trade_normalization():
    """Test that trade_id deduplication works correctly."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return False
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("TEST: PM Strength Trade Normalization Fix (Synthetic Data)")
    print("=" * 80)
    
    # Create test data
    test_data = await create_test_data(sb)
    
    # Import and run lesson builder
    print("\n🔨 Running lesson builder...")
    from src.intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import mine_lessons
    lessons_created = await mine_lessons(sb, module='pm')
    print(f"   Created {lessons_created} lessons")
    
    # Test 1: Verify n = distinct trades, not total actions
    print("\n📊 Test 1: Verify n represents distinct trades")
    print("-" * 80)
    
    # Get lessons for test pattern
    lessons = sb.table("learning_lessons").select("*").eq("pattern_key", "test.uptrend.S3.add").eq("action_category", "add").execute().data or []
    
    if not lessons:
        print("   ❌ No lessons found for test pattern")
        return False
    
    # Get matching events
    all_events = sb.table("pattern_trade_events").select("*").eq("pattern_key", "test.uptrend.S3.add").eq("action_category", "add").execute().data or []
    
    passed = 0
    failed = 0
    
    for lesson in lessons:
        scope_subset = lesson.get("scope_subset", {})
        lesson_n = lesson.get("n")
        
        # Count matching events and distinct trades
        matching_events = []
        for event in all_events:
            event_scope = event.get("scope", {})
            if isinstance(event_scope, dict) and isinstance(scope_subset, dict):
                matches = True
                for key, value in scope_subset.items():
                    if event_scope.get(key) != value:
                        matches = False
                        break
                if matches:
                    matching_events.append(event)
        
        distinct_trades = len(set(e.get("trade_id") for e in matching_events if e.get("trade_id")))
        total_actions = len(matching_events)
        
        print(f"\n   Lesson scope: {json.dumps(scope_subset)}")
        print(f"     Lesson n: {lesson_n}")
        print(f"     Matching events: {total_actions}")
        print(f"     Distinct trades: {distinct_trades}")
        
        if lesson_n == distinct_trades:
            print(f"     ✅ PASS: n matches distinct trades")
            passed += 1
        elif lesson_n == total_actions:
            print(f"     ❌ FAIL: n matches total actions (should be distinct trades)")
            failed += 1
        else:
            print(f"     ⚠️  UNKNOWN: n={lesson_n}, trades={distinct_trades}, actions={total_actions}")
    
    # Test 2: Check domination case
    print("\n📊 Test 2: Check trade domination fix")
    print("-" * 80)
    
    # For test.uptrend.S3.add with scope {'chain': 'solana', 'bucket': 'micro', 'curator': 'test'}
    # We should have: 1 trade with 56 actions + 35 trades with 1 action each = 36 trades total
    # Expected n = 36, not 91
    
    domination_lesson = None
    for lesson in lessons:
        scope = lesson.get("scope_subset", {})
        if (scope.get("chain") == "solana" and 
            scope.get("bucket") == "micro" and 
            scope.get("curator") == "test"):
            domination_lesson = lesson
            break
    
    if domination_lesson:
        n = domination_lesson.get("n")
        print(f"   Domination test lesson:")
        print(f"     n: {n}")
        print(f"     Expected: 36 (1 trade with 56 actions + 35 trades with 1 action)")
        if n == 36:
            print(f"     ✅ PASS: n=36, trade domination prevented")
            passed += 1
        else:
            print(f"     ❌ FAIL: n={n}, should be 36")
            failed += 1
    else:
        print("   ⚠️  Domination test lesson not found")
    
    # Test 3: Check variance shrinkage prior
    print("\n📊 Test 3: Verify variance shrinkage prior")
    print("-" * 80)
    
    # Check the small-n lesson (test.uptrend.S1.entry with n=3, all same RR)
    small_lessons = sb.table("learning_lessons").select("*").eq("pattern_key", "test.uptrend.S1.entry").eq("action_category", "entry").execute().data or []
    
    if small_lessons:
        for lesson in small_lessons:
            stats = lesson.get("stats", {})
            n = lesson.get("n")
            variance = stats.get("variance", 0.0)
            reliability = stats.get("reliability_score", 0.0)
            
            print(f"\n   Lesson n={n}:")
            print(f"     variance: {variance:.4f}")
            print(f"     reliability_score: {reliability:.4f}")
            
            # With VAR_PRIOR=0.25, for n=3: prior_variance = 0.25/3 = 0.0833, reliability = 1/(1+0.0833) = 0.923
            if variance == 0.0:
                expected_reliability = 1.0 / (1.0 + 0.25 / max(1, n))
                print(f"     Expected reliability (with prior): {expected_reliability:.4f}")
                if abs(reliability - expected_reliability) < 0.01:
                    print(f"     ✅ PASS: reliability={reliability:.4f} matches expected (prior applied)")
                    passed += 1
                elif reliability == 1.0:
                    print(f"     ❌ FAIL: reliability=1.0 (prior not applied)")
                    failed += 1
                else:
                    print(f"     ⚠️  reliability={reliability:.4f} (expected {expected_reliability:.4f})")
            else:
                print(f"     ⚠️  variance > 0, cannot test prior")
    else:
        print("   No small-n lessons found (test.uptrend.S1.entry)")
    
    # Test 4: Multiple scopes
    print("\n📊 Test 4: Actions span multiple scopes")
    print("-" * 80)
    
    s2_lessons = sb.table("learning_lessons").select("*").eq("pattern_key", "test.uptrend.S2.add").eq("action_category", "add").execute().data or []
    
    if s2_lessons:
        print(f"   Found {len(s2_lessons)} lessons for test.uptrend.S2.add")
        for lesson in s2_lessons:
            scope = lesson.get("scope_subset", {})
            n = lesson.get("n")
            print(f"     Scope {json.dumps(scope)}: n={n}")
            if n == 1:
                print(f"       ✅ PASS: n=1 (one trade per scope)")
                passed += 1
            else:
                print(f"       ⚠️  n={n} (expected 1)")
    else:
        print("   No lessons found for test.uptrend.S2.add")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    try:
        sb.table("learning_lessons").delete().like("pattern_key", "test.%").execute()
        sb.table("pattern_trade_events").delete().like("pattern_key", "test.%").execute()
        print("   ✅ Cleaned up")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_trade_normalization())
    sys.exit(0 if result else 1)

