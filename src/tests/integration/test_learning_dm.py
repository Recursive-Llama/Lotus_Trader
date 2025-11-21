"""
Integration test: Learning System → Decision Maker

Objective: Verify Decision Maker uses updated coefficients

Steps:
1. Create test coefficients in learning_coefficients table
2. Decision Maker evaluates new signal
3. Verify CoefficientReader reads coefficients
4. Verify allocation multiplier uses coefficients
5. Verify allocation reflects learned performance
"""

import pytest
import sys
import os

# Add src/tests to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.integration
class TestLearningDecisionMaker:
    """Test Learning System → Decision Maker integration"""
    
    def test_decision_maker_uses_learned_coefficients(
        self,
        test_db,
        test_token,
        test_curator
    ):
        """
        Verify Decision Maker uses learned coefficients for allocation.
        
        This test requires:
        - Test coefficients in learning_coefficients table
        - Decision Maker to evaluate signal
        - Verify allocation uses coefficients
        """
        # This test requires full flow - will be implemented in flow tests
        pytest.skip("Requires full flow test - see test_scenario_1b_learning_loop")

