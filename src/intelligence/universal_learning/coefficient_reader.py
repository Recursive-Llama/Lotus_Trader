"""
Coefficient Reader for Learning System

Reads learned coefficients from database and applies weight calibration and importance bleed.
Used by Decision Maker to calculate allocations based on learned performance.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from .bucket_vocabulary import BucketVocabulary

logger = logging.getLogger(__name__)


class CoefficientReader:
    """Reads and applies learned coefficients for allocation calculations"""
    
    # Weight bounds (same as CoefficientUpdater)
    WEIGHT_MIN = 0.5
    WEIGHT_MAX = 2.0
    
    # Importance bleed factor (same as CoefficientUpdater)
    IMPORTANCE_BLEED_ALPHA = 0.2
    
    def __init__(self, supabase_client):
        """
        Initialize coefficient reader.
        
        Args:
            supabase_client: Supabase client for database operations
        """
        self.sb = supabase_client
        self.bucket_vocab = BucketVocabulary()
    
    def get_timeframe_weights(
        self,
        module: str = 'dm'
    ) -> Dict[str, float]:
        """
        Get learned weights for each timeframe.
        
        Note: Timeframe weights are now stored in learning_configs table (migrated from learning_coefficients).
        Structure: learning_configs.config_data.timeframe_weights['1m'|'15m'|'1h'|'4h'].weight
        
        Args:
            module: Module identifier ('dm', 'pm', etc.) - maps to module_id 'decision_maker', 'pm', etc.
            
        Returns:
            Dictionary mapping timeframe to weight (e.g., {'1m': 0.8, '15m': 1.4, '1h': 1.1, '4h': 0.9})
        """
        timeframes = ['1m', '15m', '1h', '4h']
        weights = {}
        
        # Map module to module_id for learning_configs
        module_id_map = {
            'dm': 'decision_maker',
            'pm': 'pm',
            'ingest': 'social_ingest'
        }
        module_id = module_id_map.get(module, module)
        
        try:
            # Read timeframe weights from learning_configs
            result = (
                self.sb.table("learning_configs")
                .select("config_data")
                .eq("module_id", module_id)
                .limit(1)
                .execute()
            ).data
            
            if result and len(result) > 0:
                config_data = result[0].get('config_data', {})
                timeframe_weights = config_data.get('timeframe_weights', {})
                
                # Extract weights for each timeframe
                for tf in timeframes:
                    tf_data = timeframe_weights.get(tf, {})
                    if isinstance(tf_data, dict):
                        weight = tf_data.get('weight')
                        if weight is not None:
                            # Ensure weight is within bounds
                            weight = max(self.WEIGHT_MIN, min(self.WEIGHT_MAX, weight))
                            weights[tf] = weight
                        else:
                            weights[tf] = 1.0  # Default if no weight
                    else:
                        weights[tf] = 1.0  # Default if structure is wrong
            else:
                # No config found - use defaults
                for tf in timeframes:
                    weights[tf] = 1.0
                    
        except Exception as e:
            logger.warning(f"Error reading timeframe weights from learning_configs: {e}")
            # Fallback to defaults on error
            for tf in timeframes:
                weights[tf] = 1.0
        
        return weights
    
    def normalize_timeframe_weights(
        self,
        timeframe_weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Normalize timeframe weights so they sum to 1.0.
        
        Used for splitting total allocation across timeframes.
        
        Args:
            timeframe_weights: Dictionary of timeframe weights
            
        Returns:
            Normalized weights that sum to 1.0
        """
        total_weight = sum(timeframe_weights.values())
        
        if total_weight == 0:
            # Fallback to equal weights
            return {tf: 0.25 for tf in timeframe_weights.keys()}
        
        return {tf: w / total_weight for tf, w in timeframe_weights.items()}
    
