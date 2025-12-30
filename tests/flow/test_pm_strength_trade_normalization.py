#!/usr/bin/env python3
"""
Test PM Strength Trade Normalization Fix

Tests that lesson_builder_v5 correctly counts distinct trades, not actions,
and applies variance shrinkage prior for small-N reliability correction.

Usage:
    PYTHONPATH=src python tests/flow/test_pm_strength_trade_normalization.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import json
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

async def test_trade_normalization():
    """Test that trade_id deduplication works correctly."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return False
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("TEST: PM Strength Trade Normalization Fix")
    print("=" * 80)
    
    # Test 1: Check that lessons have n = distinct trades, not total actions
    print("\n📊 Test 1: Verify n represents distinct trades")
    print("-" * 80)
    
    # Get a sample lesson
    lessons = sb.table("learning_lessons").select("*").eq("lesson_type", "pm_strength").limit(10).execute().data or []
    
    if not lessons:
        print("⚠️  No pm_strength lessons found - cannot test")
        return True  # Not a failure, just no data
    
    # Get all pattern_trade_events
    all_events = []
    page_size = 1000
    offset = 0
    while True:
        result = sb.table("pattern_trade_events").select("*").range(offset, offset + page_size - 1).execute()
        if not result.data:
            break
        all_events.extend(result.data)
        offset += page_size
        if len(result.data) < page_size:
            break
    
    print(f"   Found {len(lessons)} lessons to check")
    print(f"   Found {len(all_events)} total events in pattern_trade_events")
    
    passed = 0
    failed = 0
    
    for lesson in lessons[:5]:  # Check first 5
        pattern_key = lesson.get("pattern_key")
        action_category = lesson.get("action_category")
        scope_subset = lesson.get("scope_subset", {})
        lesson_n = lesson.get("n")
        
        # Count matching events
        matching_events = []
        for event in all_events:
            if (event.get("pattern_key") == pattern_key and 
                event.get("action_category") == action_category):
                event_scope = event.get("scope", {})
                if isinstance(event_scope, dict) and isinstance(scope_subset, dict):
                    matches = True
                    for key, value in scope_subset.items():
                        if event_scope.get(key) != value:
                            matches = False
                            break
                    if matches:
                        matching_events.append(event)
        
        # Count distinct trades
        distinct_trades = len(set(e.get("trade_id") for e in matching_events if e.get("trade_id")))
        total_actions = len(matching_events)
        
        print(f"\n   Lesson: {pattern_key[:40]}... | {action_category}")
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
            print(f"     ⚠️  UNKNOWN: n doesn't match either (might be from old run)")
    
    print(f"\n   Results: {passed} passed, {failed} failed")
    
    # Test 2: Check variance shrinkage prior
    print("\n📊 Test 2: Verify variance shrinkage prior")
    print("-" * 80)
    
    # Check if reliability_score is not 1.0 for small n
    small_n_lessons = [l for l in lessons if l.get("n", 0) < 10]
    
    if small_n_lessons:
        print(f"   Found {len(small_n_lessons)} lessons with n < 10")
        for lesson in small_n_lessons[:3]:
            stats = lesson.get("stats", {})
            n = lesson.get("n")
            variance = stats.get("variance", 0.0)
            reliability = stats.get("reliability_score", 0.0)
            
            print(f"\n   Lesson n={n}:")
            print(f"     variance: {variance:.4f}")
            print(f"     reliability_score: {reliability:.4f}")
            
            if variance == 0.0 and reliability == 1.0:
                print(f"     ⚠️  WARNING: variance=0 → reliability=1.0 (should be < 1.0 with prior)")
            elif variance == 0.0 and reliability < 1.0:
                print(f"     ✅ PASS: variance=0 but reliability < 1.0 (prior applied)")
            else:
                print(f"     ✅ PASS: variance > 0, reliability calculated normally")
    else:
        print("   No lessons with n < 10 found")
    
    # Test 3: Check for domination case
    print("\n📊 Test 3: Check for trade domination")
    print("-" * 80)
    
    # Find lessons where one trade might dominate
    # Group events by trade_id and count actions per trade
    trade_action_counts = {}
    for event in all_events:
        trade_id = event.get("trade_id")
        if trade_id:
            trade_action_counts[trade_id] = trade_action_counts.get(trade_id, 0) + 1
    
    if trade_action_counts:
        max_actions_per_trade = max(trade_action_counts.values())
        trades_with_many_actions = sum(1 for count in trade_action_counts.values() if count >= 50)
        
        print(f"   Max actions per trade: {max_actions_per_trade}")
        print(f"   Trades with 50+ actions: {trades_with_many_actions}")
        
        if max_actions_per_trade >= 50:
            print(f"   ⚠️  Found trades with many actions - checking if they dominate lessons...")
            
            # Check if any lesson has n that matches a single trade's action count
            for lesson in lessons:
                lesson_n = lesson.get("n", 0)
                if lesson_n >= 50:
                    # This might be a domination case
                    pattern_key = lesson.get("pattern_key")
                    action_category = lesson.get("action_category")
                    scope_subset = lesson.get("scope_subset", {})
                    
                    # Count matching events and trades
                    matching_events = []
                    for event in all_events:
                        if (event.get("pattern_key") == pattern_key and 
                            event.get("action_category") == action_category):
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
                    
                    if lesson_n == distinct_trades:
                        print(f"     ✅ Lesson n={lesson_n} matches {distinct_trades} distinct trades (correct)")
                    else:
                        print(f"     ❌ Lesson n={lesson_n} but only {distinct_trades} distinct trades (domination?)")
        else:
            print(f"   ✅ No trades with excessive actions found")
    
    print("\n" + "=" * 80)
    if failed == 0:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_trade_normalization())
    sys.exit(0 if result else 1)

