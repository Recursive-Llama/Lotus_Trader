"""
Unit tests for BucketVocabulary

Tests:
1. get_mcap_bucket() - Test all bucket boundaries
2. get_vol_bucket() - Test all bucket boundaries
3. get_age_bucket() - Test all bucket boundaries
4. get_mcap_vol_ratio_bucket() - Test all bucket boundaries
5. normalize_bucket() - Test normalization of various formats
"""

import pytest
from intelligence.universal_learning.bucket_vocabulary import BucketVocabulary


class TestBucketVocabulary:
    """Test BucketVocabulary bucket calculations"""
    
    def test_get_mcap_bucket(self):
        """Test market cap bucket boundaries"""
        vocab = BucketVocabulary()
        
        # Test boundary values
        assert vocab.get_mcap_bucket(0) == "<500k"
        assert vocab.get_mcap_bucket(499_999) == "<500k"
        assert vocab.get_mcap_bucket(500_000) == "500k-1m"
        assert vocab.get_mcap_bucket(1_000_000) == "1m-2m"
        assert vocab.get_mcap_bucket(2_000_000) == "2m-5m"
        assert vocab.get_mcap_bucket(5_000_000) == "5m-10m"
        assert vocab.get_mcap_bucket(10_000_000) == "10m-50m"
        assert vocab.get_mcap_bucket(50_000_000) == "50m+"
        assert vocab.get_mcap_bucket(100_000_000) == "50m+"
    
    def test_get_vol_bucket(self):
        """Test volume bucket boundaries"""
        vocab = BucketVocabulary()
        
        # Test boundary values
        assert vocab.get_vol_bucket(0) == "<10k"
        assert vocab.get_vol_bucket(9_999) == "<10k"
        assert vocab.get_vol_bucket(10_000) == "10k-50k"
        assert vocab.get_vol_bucket(50_000) == "50k-100k"
        assert vocab.get_vol_bucket(100_000) == "100k-250k"
        assert vocab.get_vol_bucket(250_000) == "250k-500k"
        assert vocab.get_vol_bucket(500_000) == "500k-1m"
        assert vocab.get_vol_bucket(1_000_000) == "1m+"
        assert vocab.get_vol_bucket(10_000_000) == "1m+"
    
    def test_get_age_bucket(self):
        """Test age bucket boundaries"""
        vocab = BucketVocabulary()
        
        # Test boundary values
        assert vocab.get_age_bucket(0) == "<1d"
        assert vocab.get_age_bucket(0.9) == "<1d"
        assert vocab.get_age_bucket(1) == "1-3d"
        assert vocab.get_age_bucket(3) == "3-7d"
        assert vocab.get_age_bucket(7) == "7-14d"
        assert vocab.get_age_bucket(14) == "14-30d"
        assert vocab.get_age_bucket(30) == "30-90d"
        assert vocab.get_age_bucket(90) == "90d+"
        assert vocab.get_age_bucket(365) == "90d+"
    
    def test_get_mcap_vol_ratio_bucket(self):
        """Test mcap/volume ratio bucket boundaries"""
        vocab = BucketVocabulary()
        
        # Test boundary values
        assert vocab.get_mcap_vol_ratio_bucket(1_000_000, 0) == "5.0+"  # No volume
        
        # Test values just below boundaries (should be in lower bucket)
        assert vocab.get_mcap_vol_ratio_bucket(99_000, 1_000_000) == "<0.1"  # ratio = 0.099 (< 0.1)
        assert vocab.get_mcap_vol_ratio_bucket(499_000, 1_000_000) == "0.1-0.5"  # ratio = 0.499 (< 0.5)
        assert vocab.get_mcap_vol_ratio_bucket(999_000, 1_000_000) == "0.5-1.0"  # ratio = 0.999 (< 1.0)
        assert vocab.get_mcap_vol_ratio_bucket(1_999_000, 1_000_000) == "1.0-2.0"  # ratio = 1.999 (< 2.0)
        assert vocab.get_mcap_vol_ratio_bucket(4_999_000, 1_000_000) == "2.0-5.0"  # ratio = 4.999 (< 5.0)
        
        # Test values at boundaries (should be in upper bucket due to < check)
        assert vocab.get_mcap_vol_ratio_bucket(100_000, 1_000_000) == "0.1-0.5"  # ratio = 0.1 (not < 0.1, so goes to 0.1-0.5)
        assert vocab.get_mcap_vol_ratio_bucket(500_000, 1_000_000) == "0.5-1.0"  # ratio = 0.5 (not < 0.5, so goes to 0.5-1.0)
        assert vocab.get_mcap_vol_ratio_bucket(1_000_000, 1_000_000) == "1.0-2.0"  # ratio = 1.0 (not < 1.0, so goes to 1.0-2.0)
        assert vocab.get_mcap_vol_ratio_bucket(2_000_000, 1_000_000) == "2.0-5.0"  # ratio = 2.0 (not < 2.0, so goes to 2.0-5.0)
        assert vocab.get_mcap_vol_ratio_bucket(5_000_000, 1_000_000) == "5.0+"  # ratio = 5.0 (not < 5.0, so goes to 5.0+)
        assert vocab.get_mcap_vol_ratio_bucket(10_000_000, 1_000_000) == "5.0+"  # ratio = 10.0 (> 5.0)
    
    def test_normalize_bucket_mcap(self):
        """Test mcap bucket normalization"""
        vocab = BucketVocabulary()
        
        # Test standard buckets (should return as-is)
        assert vocab.normalize_bucket('mcap', '<500k') == "<500k"
        assert vocab.normalize_bucket('mcap', '500k-1m') == "500k-1m"
        assert vocab.normalize_bucket('mcap', '50m+') == "50m+"
        
        # Test case-insensitive
        assert vocab.normalize_bucket('mcap', '<500K') == "<500k"
        assert vocab.normalize_bucket('mcap', '50M+') == "50m+"
        
        # Test non-standard (should return as-is if no match)
        assert vocab.normalize_bucket('mcap', 'custom_bucket') == "custom_bucket"
    
    def test_normalize_bucket_vol(self):
        """Test volume bucket normalization"""
        vocab = BucketVocabulary()
        
        assert vocab.normalize_bucket('vol', '<10k') == "<10k"
        assert vocab.normalize_bucket('vol', '1m+') == "1m+"
        assert vocab.normalize_bucket('vol', '<10K') == "<10k"  # Case-insensitive
    
    def test_normalize_bucket_age(self):
        """Test age bucket normalization"""
        vocab = BucketVocabulary()
        
        assert vocab.normalize_bucket('age', '<1d') == "<1d"
        assert vocab.normalize_bucket('age', '90d+') == "90d+"
        assert vocab.normalize_bucket('age', '<1D') == "<1d"  # Case-insensitive
    
    def test_normalize_bucket_mcap_vol_ratio(self):
        """Test mcap/vol ratio bucket normalization"""
        vocab = BucketVocabulary()
        
        assert vocab.normalize_bucket('mcap_vol_ratio', '<0.1') == "<0.1"
        assert vocab.normalize_bucket('mcap_vol_ratio', '5.0+') == "5.0+"
    
    def test_normalize_bucket_handles_none(self):
        """Test normalization handles None/empty values"""
        vocab = BucketVocabulary()
        
        assert vocab.normalize_bucket('mcap', None) is None
        assert vocab.normalize_bucket('mcap', '') is None

