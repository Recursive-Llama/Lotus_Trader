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
    
    def get_lever_weights(
        self,
        entry_context: Dict[str, Any],
        module: str = 'dm'
    ) -> Dict[str, float]:
        """
        Get learned weights for all levers in entry context.
        
        Args:
            entry_context: Lever values at entry (curator, chain, mcap_bucket, etc.)
            module: Module identifier ('dm', 'pm', etc.)
            
        Returns:
            Dictionary mapping lever names to weights
        """
        weights = {}
        
        # Get weights for each lever
        if entry_context.get('curator'):
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'curator', entry_context['curator']
            )
            if weight:
                weights['curator'] = weight
        
        if entry_context.get('chain'):
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'chain', entry_context['chain']
            )
            if weight:
                weights['chain'] = weight
        
        if entry_context.get('mcap_bucket'):
            # Normalize bucket first
            normalized_bucket = self.bucket_vocab.normalize_bucket('mcap', entry_context['mcap_bucket'])
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'cap', normalized_bucket
            )
            if weight:
                weights['cap'] = weight
        
        if entry_context.get('vol_bucket'):
            normalized_bucket = self.bucket_vocab.normalize_bucket('vol', entry_context['vol_bucket'])
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'vol', normalized_bucket
            )
            if weight:
                weights['vol'] = weight
        
        if entry_context.get('age_bucket'):
            normalized_bucket = self.bucket_vocab.normalize_bucket('age', entry_context['age_bucket'])
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'age', normalized_bucket
            )
            if weight:
                weights['age'] = weight
        
        if entry_context.get('intent'):
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'intent', entry_context['intent']
            )
            if weight:
                weights['intent'] = weight
        
        if entry_context.get('mapping_confidence'):
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'mapping_confidence', entry_context['mapping_confidence']
            )
            if weight:
                weights['mapping_confidence'] = weight
        
        if entry_context.get('mcap_vol_ratio_bucket'):
            normalized_bucket = self.bucket_vocab.normalize_bucket('mcap_vol_ratio', entry_context['mcap_vol_ratio_bucket'])
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'mcap_vol_ratio', normalized_bucket
            )
            if weight:
                weights['mcap_vol_ratio'] = weight
        
        return weights
    
    def get_interaction_weight(
        self,
        entry_context: Dict[str, Any],
        module: str = 'dm'
    ) -> Optional[float]:
        """
        Get learned weight for interaction pattern matching entry context.
        
        Args:
            entry_context: Lever values at entry
            module: Module identifier ('dm', 'pm', etc.)
            
        Returns:
            Interaction pattern weight, or None if not found
        """
        # Generate interaction key (same logic as CoefficientUpdater)
        from .coefficient_updater import CoefficientUpdater
        updater = CoefficientUpdater(self.sb)
        interaction_key = updater.generate_interaction_key(entry_context)
        
        if interaction_key == "empty":
            return None
        
        return self._get_single_coefficient_weight(
            module, 'interaction', 'interaction', interaction_key
        )
    
    def apply_importance_bleed(
        self,
        lever_weights: Dict[str, float],
        interaction_weight: Optional[float]
    ) -> Dict[str, float]:
        """
        Apply importance bleed to lever weights when interaction pattern is active.
        
        Args:
            lever_weights: Dictionary of lever weights
            interaction_weight: Interaction pattern weight (if exists)
            
        Returns:
            Adjusted lever weights with importance bleed applied
        """
        if not interaction_weight or abs(interaction_weight - 1.0) < 0.1:
            # No bleed needed if interaction weight is neutral or doesn't exist
            return lever_weights
        
        adjusted_weights = lever_weights.copy()
        alpha = self.IMPORTANCE_BLEED_ALPHA
        
        # Apply bleed to all lever weights
        for lever_name in adjusted_weights:
            current_weight = adjusted_weights[lever_name]
            # Shrink toward 1.0 by alpha
            adjusted_weight = current_weight + alpha * (1.0 - current_weight)
            adjusted_weights[lever_name] = adjusted_weight
        
        return adjusted_weights
    
    def calculate_allocation_multiplier(
        self,
        entry_context: Dict[str, Any],
        module: str = 'dm'
    ) -> float:
        """
        Calculate total allocation multiplier from learned coefficients.
        
        Formula: multiplier = ∏(lever_weight) × interaction_weight
        
        Args:
            entry_context: Lever values at entry
            module: Module identifier ('dm', 'pm', etc.)
            
        Returns:
            Total allocation multiplier (product of all weights)
        """
        # Get single-factor weights
        lever_weights = self.get_lever_weights(entry_context, module)
        
        # Get interaction pattern weight
        interaction_weight = self.get_interaction_weight(entry_context, module)
        
        # Apply importance bleed if interaction pattern exists
        if interaction_weight:
            lever_weights = self.apply_importance_bleed(lever_weights, interaction_weight)
        
        # Calculate product of all weights
        multiplier = 1.0
        
        for lever_name, weight in lever_weights.items():
            multiplier *= weight
        
        # Apply interaction weight if it exists
        if interaction_weight:
            multiplier *= interaction_weight
        
        return multiplier
    
    def get_timeframe_weights(
        self,
        module: str = 'dm'
    ) -> Dict[str, float]:
        """
        Get learned weights for each timeframe.
        
        Note: Timeframe coefficients are stored as scope='lever', name='timeframe', key='1m' (or '15m', '1h', '4h')
        
        Args:
            module: Module identifier ('dm', 'pm', etc.)
            
        Returns:
            Dictionary mapping timeframe to weight (e.g., {'1m': 0.8, '15m': 1.4, '1h': 1.1, '4h': 0.9})
        """
        timeframes = ['1m', '15m', '1h', '4h']
        weights = {}
        
        for tf in timeframes:
            # Timeframe coefficients are stored as scope='lever', name='timeframe', key='1m' (or '15m', etc.)
            weight = self._get_single_coefficient_weight(
                module, 'lever', 'timeframe', tf
            )
            if weight:
                weights[tf] = weight
            else:
                # Default to 1.0 if no learned data
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
    
    def _get_single_coefficient_weight(
        self,
        module: str,
        scope: str,
        name: str,
        key: str
    ) -> Optional[float]:
        """
        Get weight for a single coefficient.
        
        Args:
            module: Module identifier ('dm', 'pm', etc.)
            scope: Scope ('lever', 'interaction', 'timeframe')
            name: Lever name ('curator', 'chain', 'cap', etc.)
            key: Bucket value or hashed combination
            
        Returns:
            Weight value, or None if not found
        """
        try:
            result = (
                self.sb.table("learning_coefficients")
                .select("weight")
                .eq("module", module)
                .eq("scope", scope)
                .eq("name", name)
                .eq("key", key)
                .limit(1)
                .execute()
            ).data
            
            if result and len(result) > 0:
                weight = result[0].get('weight')
                if weight is not None:
                    # Ensure weight is within bounds (should already be clamped, but double-check)
                    return max(self.WEIGHT_MIN, min(self.WEIGHT_MAX, weight))
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting coefficient weight {module}.{scope}.{name}.{key}: {e}")
            return None

