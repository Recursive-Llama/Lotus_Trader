"""
PM Thresholds Cache
Provides 5-minute caching layer for tunable thresholds with fallback precedence:
env → DB → code defaults
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client  # type: ignore

logger = logging.getLogger(__name__)


class PMThresholdsCache:
    """
    Cache for PM thresholds with 5-minute TTL.
    
    Fallback precedence:
    1. Environment variable (PM_THRESHOLD_{KEY})
    2. Database (pm_thresholds table)
    3. Code defaults
    """
    
    def __init__(self, sb_client: Optional[Client] = None):
        """
        Initialize thresholds cache.
        
        Args:
            sb_client: Optional Supabase client (creates one if not provided)
        """
        if sb_client is None:
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_KEY", "")
            if not url or not key:
                raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
            self.sb: Client = create_client(url, key)
        else:
            self.sb = sb_client
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def _get_cache_key(self, key: str, timeframe: Optional[str] = None, phase: Optional[str] = None, a_level: Optional[str] = None) -> str:
        """Generate cache key from parameters."""
        parts = [key]
        if timeframe:
            parts.append(f"tf:{timeframe}")
        if phase:
            parts.append(f"phase:{phase}")
        if a_level:
            parts.append(f"level:{a_level}")
        return "|".join(parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamp:
            return False
        age = datetime.now(timezone.utc) - self._cache_timestamp[cache_key]
        return age < self._cache_ttl
    
    def _get_from_env(self, key: str) -> Optional[Union[float, str]]:
        """Get threshold from environment variable."""
        env_key = f"PM_THRESHOLD_{key.upper()}"
        value = os.getenv(env_key)
        if value is None:
            return None
        try:
            # Try to parse as float first
            return float(value)
        except ValueError:
            # Return as string if not a number
            return value
    
    def _get_from_db(self, key: str, timeframe: Optional[str] = None, phase: Optional[str] = None, a_level: Optional[str] = None) -> Optional[Any]:
        """Get threshold from database."""
        try:
            # First, try exact match with all filters
            query = self.sb.table("pm_thresholds").select("value").eq("key", key)
            
            if timeframe:
                query = query.eq("timeframe", timeframe)
            else:
                query = query.is_("timeframe", "null")
            
            if phase:
                query = query.eq("phase", phase)
            else:
                query = query.is_("phase", "null")
            
            if a_level:
                query = query.eq("a_level", a_level)
            else:
                query = query.is_("a_level", "null")
            
            result = query.limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("value")
            
            # If no exact match, try to find most specific match by removing filters one by one
            # Try without a_level
            if a_level:
                query = self.sb.table("pm_thresholds").select("value").eq("key", key)
                if timeframe:
                    query = query.eq("timeframe", timeframe)
                else:
                    query = query.is_("timeframe", "null")
                if phase:
                    query = query.eq("phase", phase)
                else:
                    query = query.is_("phase", "null")
                query = query.is_("a_level", "null")
                result = query.limit(1).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0].get("value")
            
            # Try without phase
            if phase:
                query = self.sb.table("pm_thresholds").select("value").eq("key", key)
                if timeframe:
                    query = query.eq("timeframe", timeframe)
                else:
                    query = query.is_("timeframe", "null")
                query = query.is_("phase", "null").is_("a_level", "null")
                result = query.limit(1).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0].get("value")
            
            # Try without timeframe
            if timeframe:
                query = self.sb.table("pm_thresholds").select("value").eq("key", key).is_("timeframe", "null").is_("phase", "null").is_("a_level", "null")
                result = query.limit(1).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0].get("value")
            
            # Finally, try global default (all NULL)
            result = self.sb.table("pm_thresholds").select("value").eq("key", key).is_("timeframe", "null").is_("phase", "null").is_("a_level", "null").limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("value")
            
            return None
        except Exception as e:
            logger.warning(f"Error fetching threshold {key} from DB: {e}")
            return None
    
    def get(
        self,
        key: str,
        default: Any,
        timeframe: Optional[str] = None,
        phase: Optional[str] = None,
        a_level: Optional[str] = None
    ) -> Any:
        """
        Get threshold value with fallback precedence: env → DB → code default.
        
        Args:
            key: Threshold key (e.g., 'ts_score_aggressive')
            default: Code default value (used if env and DB don't have it)
            timeframe: Optional timeframe filter (1m, 15m, 1h, 4h)
            phase: Optional phase filter (dip, recover, euphoria, etc.)
            a_level: Optional A/E level filter (aggressive, normal, patient)
        
        Returns:
            Threshold value (from env, DB, or default)
        """
        cache_key = self._get_cache_key(key, timeframe, phase, a_level)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["value"]
        
        # Try environment variable first
        env_value = self._get_from_env(key)
        if env_value is not None:
            self._cache[cache_key] = {"value": env_value, "source": "env"}
            self._cache_timestamp[cache_key] = datetime.now(timezone.utc)
            logger.debug(f"Threshold {key} from env: {env_value}")
            return env_value
        
        # Try database
        db_value = self._get_from_db(key, timeframe, phase, a_level)
        if db_value is not None:
            self._cache[cache_key] = {"value": db_value, "source": "db"}
            self._cache_timestamp[cache_key] = datetime.now(timezone.utc)
            logger.debug(f"Threshold {key} from DB: {db_value}")
            return db_value
        
        # Use code default
        self._cache[cache_key] = {"value": default, "source": "default"}
        self._cache_timestamp[cache_key] = datetime.now(timezone.utc)
        logger.debug(f"Threshold {key} from default: {default}")
        return default
    
    def get_float(
        self,
        key: str,
        default: float,
        timeframe: Optional[str] = None,
        phase: Optional[str] = None,
        a_level: Optional[str] = None
    ) -> float:
        """
        Get threshold as float.
        
        Args:
            key: Threshold key
            default: Code default float value
            timeframe: Optional timeframe filter
            phase: Optional phase filter
            a_level: Optional A/E level filter
        
        Returns:
            Threshold value as float
        """
        value = self.get(key, default, timeframe, phase, a_level)
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return float(value)
            elif isinstance(value, dict) and "value" in value:
                return float(value["value"])
            else:
                logger.warning(f"Threshold {key} value {value} is not a number, using default {default}")
                return default
        except (ValueError, TypeError):
            logger.warning(f"Threshold {key} value {value} cannot be converted to float, using default {default}")
            return default
    
    def clear_cache(self) -> None:
        """Clear the cache (useful for testing or forced refresh)."""
        self._cache.clear()
        self._cache_timestamp.clear()
        logger.debug("Thresholds cache cleared")


# Global cache instance (lazy initialization)
_global_cache: Optional[PMThresholdsCache] = None


def get_thresholds_cache(sb_client: Optional[Client] = None) -> PMThresholdsCache:
    """
    Get or create global thresholds cache instance.
    
    Args:
        sb_client: Optional Supabase client
    
    Returns:
        Global PMThresholdsCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = PMThresholdsCache(sb_client)
    return _global_cache

