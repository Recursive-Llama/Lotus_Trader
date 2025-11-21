"""
Bucket Vocabulary for Learning System

Standardized buckets for consistent pattern matching and aggregation.
Used by Decision Maker and Learning System to ensure consistent bucketing.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BucketVocabulary:
    """Standardized bucket definitions for learning system"""
    
    # Market Cap buckets (USD)
    MCAP_BUCKETS = [
        "<500k",
        "500k-1m",
        "1m-2m",
        "2m-5m",
        "5m-10m",
        "10m-50m",
        "50m+"
    ]
    
    # Volume buckets (24h USD)
    VOL_BUCKETS = [
        "<10k",
        "10k-50k",
        "50k-100k",
        "100k-250k",
        "250k-500k",
        "500k-1m",
        "1m+"
    ]
    
    # Age buckets (days since launch)
    AGE_BUCKETS = [
        "<1d",
        "1-3d",
        "3-7d",
        "7-14d",
        "14-30d",
        "30-90d",
        "90d+"
    ]
    
    # Mcap/Volume Ratio buckets
    MCAP_VOL_RATIO_BUCKETS = [
        "<0.1",
        "0.1-0.5",
        "0.5-1.0",
        "1.0-2.0",
        "2.0-5.0",
        "5.0+"
    ]
    
    @staticmethod
    def get_mcap_bucket(mcap_usd: float) -> str:
        """
        Get market cap bucket for a given market cap value.
        
        Args:
            mcap_usd: Market cap in USD
            
        Returns:
            Bucket string (e.g., "1m-2m")
        """
        if mcap_usd < 500_000:
            return "<500k"
        elif mcap_usd < 1_000_000:
            return "500k-1m"
        elif mcap_usd < 2_000_000:
            return "1m-2m"
        elif mcap_usd < 5_000_000:
            return "2m-5m"
        elif mcap_usd < 10_000_000:
            return "5m-10m"
        elif mcap_usd < 50_000_000:
            return "10m-50m"
        else:
            return "50m+"
    
    @staticmethod
    def get_vol_bucket(vol_24h_usd: float) -> str:
        """
        Get volume bucket for a given 24h volume value.
        
        Args:
            vol_24h_usd: 24h volume in USD
            
        Returns:
            Bucket string (e.g., "250k-500k")
        """
        if vol_24h_usd < 10_000:
            return "<10k"
        elif vol_24h_usd < 50_000:
            return "10k-50k"
        elif vol_24h_usd < 100_000:
            return "50k-100k"
        elif vol_24h_usd < 250_000:
            return "100k-250k"
        elif vol_24h_usd < 500_000:
            return "250k-500k"
        elif vol_24h_usd < 1_000_000:
            return "500k-1m"
        else:
            return "1m+"
    
    @staticmethod
    def get_age_bucket(age_days: float) -> str:
        """
        Get age bucket for a given age in days.
        
        Args:
            age_days: Age in days since launch
            
        Returns:
            Bucket string (e.g., "3-7d")
        """
        if age_days < 1:
            return "<1d"
        elif age_days < 3:
            return "1-3d"
        elif age_days < 7:
            return "3-7d"
        elif age_days < 14:
            return "7-14d"
        elif age_days < 30:
            return "14-30d"
        elif age_days < 90:
            return "30-90d"
        else:
            return "90d+"
    
    @staticmethod
    def get_mcap_vol_ratio_bucket(mcap_usd: float, vol_24h_usd: float) -> str:
        """
        Get mcap/volume ratio bucket.
        
        Args:
            mcap_usd: Market cap in USD
            vol_24h_usd: 24h volume in USD
            
        Returns:
            Bucket string (e.g., "0.5-1.0")
        """
        if vol_24h_usd == 0:
            return "5.0+"  # High ratio if no volume
        
        ratio = mcap_usd / vol_24h_usd
        
        if ratio < 0.1:
            return "<0.1"
        elif ratio < 0.5:
            return "0.1-0.5"
        elif ratio < 1.0:
            return "0.5-1.0"
        elif ratio < 2.0:
            return "1.0-2.0"
        elif ratio < 5.0:
            return "2.0-5.0"
        else:
            return "5.0+"
    
    @staticmethod
    def normalize_bucket(bucket_type: str, bucket_value: str) -> Optional[str]:
        """
        Normalize a bucket value to standard format.
        
        This is useful when entry_context has slightly different bucket formats.
        Attempts to map to standard buckets.
        
        Args:
            bucket_type: Type of bucket ('mcap', 'vol', 'age', 'mcap_vol_ratio')
            bucket_value: Current bucket value
            
        Returns:
            Normalized bucket string, or None if can't be normalized
        """
        if not bucket_value:
            return None
        
        bucket_value = bucket_value.strip()
        
        if bucket_type == 'mcap':
            # Try to match to standard buckets
            for standard_bucket in BucketVocabulary.MCAP_BUCKETS:
                if bucket_value.lower() == standard_bucket.lower():
                    return standard_bucket
            # If no match, return as-is (might be a new bucket format)
            return bucket_value
        
        elif bucket_type == 'vol':
            for standard_bucket in BucketVocabulary.VOL_BUCKETS:
                if bucket_value.lower() == standard_bucket.lower():
                    return standard_bucket
            return bucket_value
        
        elif bucket_type == 'age':
            for standard_bucket in BucketVocabulary.AGE_BUCKETS:
                if bucket_value.lower() == standard_bucket.lower():
                    return standard_bucket
            return bucket_value
        
        elif bucket_type == 'mcap_vol_ratio':
            for standard_bucket in BucketVocabulary.MCAP_VOL_RATIO_BUCKETS:
                if bucket_value.lower() == standard_bucket.lower():
                    return standard_bucket
            return bucket_value
        
        return bucket_value

