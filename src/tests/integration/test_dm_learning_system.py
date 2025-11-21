"""
Integration test: Decision Maker → Learning System

Objective: Verify Decision Maker creates positions that learning system can process

Steps:
1. Decision Maker creates position with entry_context
2. Position closes
3. Learning system processes position_closed strand
4. Verify entry_context from strand matches position's entry_context
5. Verify coefficients updated for all levers in entry_context
"""

import pytest
import sys
import os
from datetime import datetime, timezone

# Add src/tests to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from test_helpers import get_positions_by_token, get_strand_by_id, get_coefficient


@pytest.mark.integration
class TestDecisionMakerLearningSystem:
    """Test Decision Maker → Learning System integration"""
    
    def test_entry_context_preserved_through_closure(
        self,
        test_db,
        test_token,
        test_curator
    ):
        """
        Verify entry_context is preserved when position closes and learning system processes it.
        
        This is a flow test that requires:
        - Decision Maker to create position with entry_context
        - PM to close position and emit position_closed strand
        - Learning system to process strand
        """
        # This test requires full flow - will be implemented in flow tests
        # For now, this is a placeholder structure
        pytest.skip("Requires full flow test - see test_scenario_1b_learning_loop")

