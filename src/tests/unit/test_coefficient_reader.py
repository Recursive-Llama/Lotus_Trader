"""
Unit tests for CoefficientReader

Tests:
1. get_lever_weights() - Test reading all levers
2. get_interaction_weight() - Test reading interaction patterns
3. apply_importance_bleed() - Test bleed application
4. calculate_allocation_multiplier() - Test multiplier calculation
5. get_timeframe_weights() - Test timeframe weight reading
6. normalize_timeframe_weights() - Test normalization
"""

import pytest
from unittest.mock import Mock
from intelligence.universal_learning.coefficient_reader import CoefficientReader


class TestCoefficientReader:
    """Test CoefficientReader functionality"""
    
    @pytest.fixture
    def reader(self):
        """Create CoefficientReader instance with mocked Supabase client"""
        mock_sb = Mock()
        return CoefficientReader(mock_sb)
    
    def test_get_timeframe_weights(self, reader):
        """Test timeframe weight reading"""
        # Mock Supabase to return timeframe weights
        mock_sb = Mock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"weight": 0.8}  # For 1m
        ]
        
        reader = CoefficientReader(mock_sb)
        
        # Should return weights for all timeframes
        weights = reader.get_timeframe_weights()
        
        # Should have all 4 timeframes
        assert "1m" in weights
        assert "15m" in weights
        assert "1h" in weights
        assert "4h" in weights
    
    def test_normalize_timeframe_weights(self, reader):
        """Test timeframe weight normalization"""
        weights = {
            "1m": 0.8,
            "15m": 1.4,
            "1h": 1.1,
            "4h": 0.9
        }
        
        normalized = reader.normalize_timeframe_weights(weights)
        
        # Should sum to 1.0
        assert abs(sum(normalized.values()) - 1.0) < 0.001
        
        # Should preserve relative ratios
        assert normalized["15m"] > normalized["1h"] > normalized["4h"] > normalized["1m"]
    
    def test_normalize_timeframe_weights_zero_total(self, reader):
        """Test normalization handles zero total"""
        weights = {
            "1m": 0.0,
            "15m": 0.0,
            "1h": 0.0,
            "4h": 0.0
        }
        
        normalized = reader.normalize_timeframe_weights(weights)
        
        # Should fallback to equal weights
        assert all(w == 0.25 for w in normalized.values())
    
    def test_calculate_allocation_multiplier(self, reader):
        """Test allocation multiplier calculation"""
        # Mock Supabase to return lever weights
        mock_sb = Mock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"weight": 1.2}  # For curator
        ]
        
        reader = CoefficientReader(mock_sb)
        
        entry_context = {
            "curator": "0xdetweiler",
            "chain": "solana"
        }
        
        multiplier = reader.calculate_allocation_multiplier(entry_context)
        
        # Should return a multiplier (product of weights)
        assert multiplier > 0
        assert isinstance(multiplier, float)
    
    def test_apply_importance_bleed(self, reader):
        """Test importance bleed application"""
        lever_weights = {
            "curator": 1.5,
            "chain": 1.3
        }
        
        # Neutral interaction weight should not apply bleed
        result = reader.apply_importance_bleed(lever_weights, 1.0)
        assert result == lever_weights
        
        # Significant interaction weight should apply bleed
        result = reader.apply_importance_bleed(lever_weights, 1.5)
        
        # Adjusted weights should be between original and 1.0
        assert 1.0 <= result["curator"] <= 1.5
        assert 1.0 <= result["chain"] <= 1.3


