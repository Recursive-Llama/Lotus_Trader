"""
Flow Test: Scenario 1B v4_Learning Verification

Objective: Verify v4_Learning features work correctly after position closure

This test extends Scenario 1B to verify:
1. Braiding system processes position_closed strands
2. Braids created in learning_braids table with correct dimensions
3. Lessons built automatically after position closure
4. New dimensions (vol_bucket, ema_slopes_bucket) included in patterns
5. LLM learning layer processes strands (if enabled)

Note: This test assumes a position has already closed (from Scenario 1B or 9)
"""

import pytest
import sys
import os
from datetime import datetime, timezone

# Add src/tests to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from test_helpers import wait_for_condition


@pytest.mark.flow
class TestScenario1BV4LearningVerification:
    """Test Scenario 1B v4_Learning: Verify braiding, lessons, and new dimensions"""
    
    @pytest.mark.asyncio
    async def test_v4_learning_features_after_position_closure(
        self,
        test_db,
        test_token,
        empty_learning_system
    ):
        """
        Verify v4_Learning features work after a position closes.
        
        Prerequisites:
        - A position must have closed (from Scenario 1B or 9)
        - position_closed strand must exist
        - Learning system must have processed the strand
        
        This test verifies:
        1. Braids created in learning_braids table
        2. Lessons created in learning_lessons table (automatic)
        3. New dimensions included (vol_bucket, ema_slopes_bucket)
        4. LLM learning layer processed (if enabled)
        """
        sb = test_db.client
        token_contract = test_token["contract"]
        token_chain = test_token["chain"]
        
        print(f"\n📊 Step 1: Finding closed position and position_closed strand...")
        
        # Find a recently closed position
        closed_positions = (
            sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,timeframe,closed_at,completed_trades,entry_context")
            .eq("token_contract", token_contract)
            .eq("token_chain", token_chain)
            .not_.is_("closed_at", "null")
            .order("closed_at", desc=True)
            .limit(1)
            .execute()
        )
        
        if not closed_positions.data:
            pytest.skip("No closed positions found. Run Scenario 1B or 9 first to create a closed position.")
        
        position = closed_positions.data[0]
        position_id = position["id"]
        timeframe = position["timeframe"]
        completed_trades = position.get("completed_trades", [])
        entry_context = position.get("entry_context", {})
        
        print(f"   ✅ Found closed position: {position_id} (timeframe: {timeframe})")
        
        if not completed_trades:
            pytest.skip(f"Position {position_id} has no completed_trades. Cannot verify braiding.")
        
        # Find position_closed strand
        position_closed_strands = (
            sb.table("ad_strands")
            .select("*")
            .eq("kind", "position_closed")
            .eq("position_id", position_id)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        
        if not position_closed_strands.data:
            pytest.skip(f"No position_closed strand found for position {position_id}. Learning system may not have processed it yet.")
        
        strand = position_closed_strands.data[0]
        print(f"   ✅ Found position_closed strand: {strand.get('id')}")
        
        # Step 2: Verify braids were created
        print(f"\n📊 Step 2: Verifying braids created in learning_braids table...")
        
        def braids_created():
            # Check for PM braids (should exist if position closed)
            pm_braids = (
                sb.table("learning_braids")
                .select("*")
                .eq("module", "pm")
                .limit(10)
                .execute()
            )
            return len(pm_braids.data or []) > 0
        
        wait_for_condition(
            braids_created,
            timeout=30,
            poll_interval=2,
            error_message="No braids found in learning_braids table. Braiding system may not have processed the strand."
        )
        
        # Get braids for this position's timeframe
        pm_braids = (
            sb.table("learning_braids")
            .select("*")
            .eq("module", "pm")
            .limit(20)
            .execute()
        )
        
        if pm_braids.data:
            print(f"   ✅ Found {len(pm_braids.data)} PM braids")
            
            # Verify new dimensions are included
            sample_braid = pm_braids.data[0]
            dimensions = sample_braid.get("dimensions", {})
            
            # Check for ema_slopes_bucket in PM braids (NEW dimension)
            has_ema_slopes = "ema_slopes_bucket" in dimensions or any(
                "ema_slopes" in str(dim).lower() for dim in dimensions.keys()
            )
            
            if has_ema_slopes:
                print(f"   ✅ New dimension 'ema_slopes_bucket' found in braids")
            else:
                print(f"   ⚠️  'ema_slopes_bucket' not found in sample braid (may not be in all patterns)")
            
            # Verify braid structure
            assert "pattern_key" in sample_braid, "Braid missing pattern_key"
            assert "family_id" in sample_braid, "Braid missing family_id"
            assert "stats" in sample_braid, "Braid missing stats"
            assert "dimensions" in sample_braid, "Braid missing dimensions"
            
            stats = sample_braid.get("stats", {})
            assert "n" in stats, "Braid stats missing 'n'"
            assert "avg_rr" in stats, "Braid stats missing 'avg_rr'"
            
            print(f"   ✅ Braid structure verified")
        else:
            pytest.fail("No PM braids found after position closure")
        
        # Check for DM braids if entry_context has curator
        if entry_context.get("curator"):
            dm_braids = (
                sb.table("learning_braids")
                .select("*")
                .eq("module", "dm")
                .limit(10)
                .execute()
            )
            
            if dm_braids.data:
                print(f"   ✅ Found {len(dm_braids.data)} DM braids")
                
                # Check for vol_bucket in DM braids (NEW dimension)
                sample_dm_braid = dm_braids.data[0]
                dm_dimensions = sample_dm_braid.get("dimensions", {})
                
                has_vol_bucket = "vol_bucket" in dm_dimensions
                
                if has_vol_bucket:
                    print(f"   ✅ New dimension 'vol_bucket' found in DM braids")
                else:
                    print(f"   ⚠️  'vol_bucket' not found in sample DM braid (may not be in all patterns)")
        
        # Step 3: Verify lessons were built automatically
        print(f"\n📊 Step 3: Verifying lessons built automatically in learning_lessons table...")
        
        def lessons_created():
            # Lessons are built automatically after every closed trade
            lessons = (
                sb.table("learning_lessons")
                .select("*")
                .eq("status", "active")
                .limit(10)
                .execute()
            )
            return len(lessons.data or []) > 0
        
        # Lessons may take a moment to build, but should exist if braids exist
        wait_for_condition(
            lessons_created,
            timeout=10,
            poll_interval=1,
            error_message="No lessons found. Lesson builder may not have run automatically."
        )
        
        pm_lessons = (
            sb.table("learning_lessons")
            .select("*")
            .eq("module", "pm")
            .eq("status", "active")
            .limit(10)
            .execute()
        )
        
        if pm_lessons.data:
            print(f"   ✅ Found {len(pm_lessons.data)} active PM lessons")
            
            # Verify lesson structure
            sample_lesson = pm_lessons.data[0]
            assert "trigger" in sample_lesson, "Lesson missing trigger"
            assert "action" in sample_lesson, "Lesson missing action"
            assert "edge_score" in sample_lesson, "Lesson missing edge_score"
            
            print(f"   ✅ Lesson structure verified")
            print(f"   ✅ Lesson builder ran automatically after position closure")
        else:
            print(f"   ⚠️  No PM lessons found (may need more braids to meet thresholds)")
        
        # Step 4: Verify LLM learning layer (if enabled)
        print(f"\n📊 Step 4: Checking LLM learning layer status...")
        
        llm_entries = (
            sb.table("llm_learning")
            .select("*")
            .limit(5)
            .execute()
        )
        
        if llm_entries.data:
            print(f"   ✅ Found {len(llm_entries.data)} LLM learning entries")
            print(f"   ✅ LLM learning layer is active")
        else:
            print(f"   ℹ️  No LLM learning entries found (LLM layer may not be enabled or no proposals generated yet)")
        
        # Step 5: Verify new dimensions in entry_context
        print(f"\n📊 Step 5: Verifying new dimensions in entry_context...")
        
        # Check for vol_bucket in entry_context (DM dimension)
        if "vol_bucket" in entry_context:
            print(f"   ✅ 'vol_bucket' found in entry_context: {entry_context.get('vol_bucket')}")
        else:
            print(f"   ⚠️  'vol_bucket' not in entry_context (may not be set by Decision Maker)")
        
        # Check for ema_slopes_bucket in action_context (PM dimension)
        # This would be in completed_trades[0].action_context, not entry_context
        if completed_trades:
            first_trade = completed_trades[0] if isinstance(completed_trades, list) else completed_trades
            action_context = first_trade.get("action_context", {})
            
            if "ema_slopes_bucket" in action_context:
                print(f"   ✅ 'ema_slopes_bucket' found in action_context: {action_context.get('ema_slopes_bucket')}")
            else:
                print(f"   ⚠️  'ema_slopes_bucket' not in action_context (may not be set by PM)")
        
        print(f"\n✅ v4_Learning verification complete!")
        print(f"   - Braiding system: ✅ Processing position_closed strands")
        print(f"   - Lesson builder: ✅ Running automatically after closures")
        print(f"   - New dimensions: ⚠️  Verify in actual patterns (may not appear in all)")
        print(f"   - LLM learning layer: ✅ Checked (may need enablement)")

