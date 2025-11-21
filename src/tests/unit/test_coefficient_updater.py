"""
Unit tests for CoefficientUpdater

Tests:
1. calculate_decay_weight() - Test decay over time
2. update_coefficient_ewma() - Test EWMA updates
3. generate_interaction_key() - Test key generation consistency
4. update_interaction_pattern() - Test interaction updates
5. apply_importance_bleed() - Test bleed calculation
"""

import pytest
import math
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from intelligence.universal_learning.coefficient_updater import CoefficientUpdater


class TestCoefficientUpdater:
    """Test CoefficientUpdater functionality"""
    
    @pytest.fixture
    def updater(self):
        """Create CoefficientUpdater instance with mocked Supabase client"""
        mock_sb = Mock()
        return CoefficientUpdater(mock_sb)
    
    def test_calculate_decay_weight(self, updater):
        """Test decay weight calculation"""
        now = datetime.now(timezone.utc)
        
        # Recent trade (1 day ago)
        trade_1d = now - timedelta(days=1)
        w_short_1d = updater.calculate_decay_weight(trade_1d, now, updater.TAU_SHORT)
        w_long_1d = updater.calculate_decay_weight(trade_1d, now, updater.TAU_LONG)
        
        # Old trade (30 days ago)
        trade_30d = now - timedelta(days=30)
        w_short_30d = updater.calculate_decay_weight(trade_30d, now, updater.TAU_SHORT)
        w_long_30d = updater.calculate_decay_weight(trade_30d, now, updater.TAU_LONG)
        
        # Verify decay pattern
        assert 0.0 <= w_short_1d <= 1.0
        assert 0.0 <= w_long_1d <= 1.0
        assert 0.0 <= w_short_30d <= 1.0
        assert 0.0 <= w_long_30d <= 1.0
        
        # Recent trade should have higher decay weight than old trade
        assert w_short_1d > w_short_30d
        assert w_long_1d > w_long_30d
        
        # For recent trades (1 day ago), long-term memory has higher weight
        # because it decays slower (tau_long=90 > tau_short=14)
        # This is correct: exp(-1/90) > exp(-1/14) because -1/90 > -1/14
        assert w_long_1d > w_short_1d, \
            f"Long-term weight ({w_long_1d}) should be > short-term weight ({w_short_1d}) for recent trade"
        
        # For old trades (30 days ago), short-term memory has lower weight
        # because it decays faster: exp(-30/14) < exp(-30/90)
        assert w_short_30d < w_long_30d, \
            f"Short-term weight ({w_short_30d}) should be < long-term weight ({w_long_30d}) for old trade"
        
        # Verify formula: exp(-delta_t / tau)
        expected_short_1d = math.exp(-1 / updater.TAU_SHORT)
        assert abs(w_short_1d - expected_short_1d) < 0.001
    
    def test_calculate_decay_weight_handles_future(self, updater):
        """Test decay weight handles future timestamps"""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=1)
        
        # Should handle gracefully (delta_t = 0)
        weight = updater.calculate_decay_weight(future, now, updater.TAU_SHORT)
        assert weight == 1.0  # exp(0) = 1.0
    
    def test_generate_interaction_key(self, updater):
        """Test interaction key generation consistency"""
        entry_context = {
            "curator": "0xdetweiler",
            "chain": "solana",
            "mcap_bucket": "1m-2m",
            "vol_bucket": "100k-250k",
            "age_bucket": "<7d",
            "intent": "research_positive",
            "mapping_confidence": 0.8,
            "mcap_vol_ratio_bucket": "0.5-1.0"
        }
        
        key1 = updater.generate_interaction_key(entry_context)
        key2 = updater.generate_interaction_key(entry_context)
        
        # Should be consistent
        assert key1 == key2
        
        # Should contain all relevant levers
        assert "curator=0xdetweiler" in key1
        assert "chain=solana" in key1
        assert "cap=1m-2m" in key1
        assert "vol=100k-250k" in key1
    
    def test_generate_interaction_key_empty(self, updater):
        """Test interaction key generation with empty context"""
        empty_context = {}
        key = updater.generate_interaction_key(empty_context)
        assert key == "empty"
    
    def test_generate_interaction_key_sorted(self, updater):
        """Test interaction key parts are sorted for consistency"""
        entry_context1 = {
            "curator": "A",
            "chain": "B"
        }
        entry_context2 = {
            "chain": "B",
            "curator": "A"
        }
        
        key1 = updater.generate_interaction_key(entry_context1)
        key2 = updater.generate_interaction_key(entry_context2)
        
        # Should be same regardless of order
        assert key1 == key2
    
    def test_apply_importance_bleed_neutral(self, updater):
        """Test importance bleed with neutral interaction weight"""
        entry_context = {"curator": "test"}
        lever_weights = {"curator": 1.5}
        
        # Neutral weight (1.0) should not apply bleed
        result = updater.apply_importance_bleed(entry_context, 1.0)
        assert result == {}
    
    def test_apply_importance_bleed_insignificant(self, updater):
        """Test importance bleed with insignificant interaction weight"""
        entry_context = {"curator": "test"}
        
        # Weight close to 1.0 (within 0.1) should not apply bleed
        result = updater.apply_importance_bleed(entry_context, 1.05)
        assert result == {}
    
    def test_apply_importance_bleed_significant(self, updater):
        """Test importance bleed with significant interaction weight"""
        # Mock Supabase to return existing weight
        mock_sb = Mock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"weight": 1.5}
        ]
        
        updater = CoefficientUpdater(mock_sb)
        entry_context = {"curator": "test"}
        
        # Significant weight (1.5) should apply bleed
        result = updater.apply_importance_bleed(entry_context, 1.5)
        
        # Should return adjusted weights
        assert "curator" in result
        lever_key, adjusted_weight = result["curator"]
        assert lever_key == "test"
        # Adjusted weight should be between 1.0 and 1.5 (shrunk toward 1.0)
        assert 1.0 <= adjusted_weight <= 1.5

