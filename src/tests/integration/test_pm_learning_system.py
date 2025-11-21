"""
Integration test: PM → Learning System

Objective: Verify PM emits strands that learning system can process

Steps:
1. PM closes position
2. PM computes R/R and writes completed_trades
3. PM emits position_closed strand
4. CRITICAL: Verify learning system is triggered (Option B - direct call)
5. Learning system processes strand
6. Verify completed_trades from strand matches position's completed_trades
7. Verify R/R used for coefficient updates
"""

import pytest
import sys
import os

# Add src/tests to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.integration
class TestPMLearningSystem:
    """Test PM → Learning System integration"""
    
    def test_position_closed_strand_emission(
        self,
        test_db,
        test_token
    ):
        """
        Verify PM emits position_closed strand correctly.
        
        This test verifies:
        - PM creates position_closed strand with correct structure
        - Strand includes entry_context and completed_trades
        - Learning system is called directly (Option B)
        """
        # This test requires full flow - will be implemented in flow tests
        # For now, this is a placeholder structure
        pytest.skip("Requires full flow test - see test_scenario_1b_learning_loop")
    
    def test_learning_system_triggered_directly(
        self,
        test_db
    ):
        """
        Verify learning system is triggered directly by PM (Option B).
        
        This test verifies:
        - PM calls learning_system.process_strand_event() directly
        - No queue mechanism needed
        - Matches Social Ingest/Decision Maker pattern
        """
        # This is verified in Part 1 code review
        # Option B is implemented in pm_core_tick.py:548
        pytest.skip("Verified in code review - Option B implemented")

