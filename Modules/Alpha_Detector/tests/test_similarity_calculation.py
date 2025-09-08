"""
Test Similarity Calculation in Isolation
"""

import pytest
from unittest.mock import Mock

from src.intelligence.system_control.central_intelligence_layer.meta_signals.confluence_detector import ConfluenceDetector
from src.intelligence.system_control.central_intelligence_layer.meta_signals.lead_lag_predictor import LeadLagPredictor
from src.intelligence.system_control.central_intelligence_layer.meta_signals.transfer_hit_detector import TransferHitDetector


class TestSimilarityCalculation:
    """Test similarity calculation methods in isolation"""
    
    @pytest.fixture
    def confluence_detector(self):
        return ConfluenceDetector(Mock())
    
    @pytest.fixture
    def lead_lag_predictor(self):
        return LeadLagPredictor(Mock())
    
    @pytest.fixture
    def transfer_hit_detector(self):
        return TransferHitDetector(Mock())
    
    def test_confluence_pattern_similarity_perfect_match(self, confluence_detector):
        """Test confluence detector similarity calculation with perfect match"""
        patterns1 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            }
        ]
        
        patterns2 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            }
        ]
        
        similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns2)
        assert similarity == 1.0  # Perfect match
    
    def test_confluence_pattern_similarity_no_match(self, confluence_detector):
        """Test confluence detector similarity calculation with no match"""
        patterns1 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            }
        ]
        
        patterns2 = [
            {
                'symbol': 'ETH',
                'timeframe': '4h',
                'regime': 'low_vol',
                'session_bucket': 'EU',
                'tags': ['agent:other:pattern'],
                'module_intelligence': {'pattern_type': 'volume_spike'}
            }
        ]
        
        similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns2)
        # Even completely different patterns share 'signal_strength:unknown' feature
        # So we get a small non-zero similarity (1/13 ≈ 0.077)
        assert 0.07 < similarity < 0.08  # Small similarity due to shared 'unknown' features
    
    def test_confluence_pattern_similarity_partial_match(self, confluence_detector):
        """Test confluence detector similarity calculation with partial match"""
        patterns1 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            }
        ]
        
        patterns2 = [
            {
                'symbol': 'BTC',  # Same symbol
                'timeframe': '4h',  # Different timeframe
                'regime': 'high_vol',  # Same regime
                'session_bucket': 'EU',  # Different session
                'tags': ['agent:other:pattern'],  # Different tags
                'module_intelligence': {'pattern_type': 'divergence'}  # Same pattern type
            }
        ]
        
        similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns2)
        # Should be > 0 but < 1.0 due to partial matches
        assert 0.0 < similarity < 1.0
        print(f"Partial match similarity: {similarity}")
    
    def test_lead_lag_strand_similarity_perfect_match(self, lead_lag_predictor):
        """Test lead-lag predictor strand similarity with perfect match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        strand2 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        similarity = lead_lag_predictor._calculate_strand_similarity(strand1, strand2)
        assert similarity == 1.0  # Perfect match
    
    def test_lead_lag_strand_similarity_no_match(self, lead_lag_predictor):
        """Test lead-lag predictor strand similarity with no match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        strand2 = {
            'symbol': 'ETH',
            'timeframe': '4h',
            'regime': 'low_vol',
            'session_bucket': 'EU',
            'tags': ['agent:other:pattern'],
            'module_intelligence': {'pattern_type': 'volume_spike'}
        }
        
        similarity = lead_lag_predictor._calculate_strand_similarity(strand1, strand2)
        assert similarity == 0.0  # No match
    
    def test_lead_lag_strand_similarity_partial_match(self, lead_lag_predictor):
        """Test lead-lag predictor strand similarity with partial match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'}
        }
        
        strand2 = {
            'symbol': 'BTC',  # Same symbol
            'timeframe': '4h',  # Different timeframe
            'regime': 'high_vol',  # Same regime
            'session_bucket': 'EU',  # Different session
            'tags': ['agent:other:pattern'],  # Different tags
            'module_intelligence': {'pattern_type': 'divergence'}  # Same pattern type
        }
        
        similarity = lead_lag_predictor._calculate_strand_similarity(strand1, strand2)
        # Should be > 0 but < 1.0 due to partial matches
        assert 0.0 < similarity < 1.0
        print(f"Lead-lag partial match similarity: {similarity}")
    
    def test_transfer_hit_pattern_similarity_perfect_match(self, transfer_hit_detector):
        """Test transfer hit detector pattern similarity with perfect match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'},
            'sig_sigma': 0.8
        }
        
        strand2 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'},
            'sig_sigma': 0.8
        }
        
        similarity = transfer_hit_detector._calculate_pattern_similarity(strand1, strand2)
        assert similarity == 1.0  # Perfect match
    
    def test_transfer_hit_pattern_similarity_no_match(self, transfer_hit_detector):
        """Test transfer hit detector pattern similarity with no match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'},
            'sig_sigma': 0.8
        }
        
        strand2 = {
            'symbol': 'ETH',
            'timeframe': '4h',
            'regime': 'low_vol',
            'session_bucket': 'EU',
            'tags': ['agent:other:pattern'],
            'module_intelligence': {'pattern_type': 'volume_spike'},
            'sig_sigma': 0.2
        }
        
        similarity = transfer_hit_detector._calculate_pattern_similarity(strand1, strand2)
        # Even completely different patterns share some common features
        # So we get a small non-zero similarity
        assert 0.07 < similarity < 0.09  # Small similarity due to shared features
    
    def test_transfer_hit_pattern_similarity_partial_match(self, transfer_hit_detector):
        """Test transfer hit detector pattern similarity with partial match"""
        strand1 = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'regime': 'high_vol',
            'session_bucket': 'US',
            'tags': ['agent:test:pattern'],
            'module_intelligence': {'pattern_type': 'divergence'},
            'sig_sigma': 0.8
        }
        
        strand2 = {
            'symbol': 'BTC',  # Same symbol
            'timeframe': '4h',  # Different timeframe
            'regime': 'high_vol',  # Same regime
            'session_bucket': 'EU',  # Different session
            'tags': ['agent:other:pattern'],  # Different tags
            'module_intelligence': {'pattern_type': 'divergence'},  # Same pattern type
            'sig_sigma': 0.9  # Similar signal strength
        }
        
        similarity = transfer_hit_detector._calculate_pattern_similarity(strand1, strand2)
        # Should be > 0 but < 1.0 due to partial matches
        assert 0.0 < similarity < 1.0
        print(f"Transfer hit partial match similarity: {similarity}")
    
    def test_similarity_calculation_consistency(self, confluence_detector, lead_lag_predictor, transfer_hit_detector):
        """Test that all similarity calculation methods are consistent"""
        # Test data
        patterns1 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'},
                'sig_sigma': 0.8
            }
        ]
        
        patterns2 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'},
                'sig_sigma': 0.8
            }
        ]
        
        strand1 = patterns1[0]
        strand2 = patterns2[0]
        
        # All should return 1.0 for perfect matches
        confluence_similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns2)
        lead_lag_similarity = lead_lag_predictor._calculate_strand_similarity(strand1, strand2)
        transfer_similarity = transfer_hit_detector._calculate_pattern_similarity(strand1, strand2)
        
        assert confluence_similarity == 1.0
        assert lead_lag_similarity == 1.0
        assert transfer_similarity == 1.0
        
        print(f"All similarity methods return 1.0 for perfect matches:")
        print(f"  Confluence: {confluence_similarity}")
        print(f"  Lead-Lag: {lead_lag_similarity}")
        print(f"  Transfer: {transfer_similarity}")
    
    def test_similarity_calculation_edge_cases(self, confluence_detector):
        """Test edge cases in similarity calculation"""
        # Empty patterns
        empty_patterns = []
        normal_patterns = [{'symbol': 'BTC', 'timeframe': '1h'}]
        
        similarity = confluence_detector._calculate_pattern_similarity(empty_patterns, normal_patterns)
        assert similarity == 0.0
        
        # None patterns
        similarity = confluence_detector._calculate_pattern_similarity(None, normal_patterns)
        assert similarity == 0.0
        
        # Patterns with missing fields
        incomplete_patterns = [{'symbol': 'BTC'}]  # Missing other fields
        complete_patterns = [{'symbol': 'BTC', 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'}]
        
        similarity = confluence_detector._calculate_pattern_similarity(incomplete_patterns, complete_patterns)
        assert 0.0 < similarity < 1.0  # Should have some similarity due to matching symbol


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
