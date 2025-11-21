"""
Coefficient Updater for Learning System

Implements EWMA with temporal decay, interaction patterns, and importance bleed.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import math

from .bucket_vocabulary import BucketVocabulary

logger = logging.getLogger(__name__)


class CoefficientUpdater:
    """Handles coefficient updates with EWMA, interaction patterns, and importance bleed"""
    
    # Time constants for EWMA
    TAU_SHORT = 14  # days (fast memory)
    TAU_LONG = 90   # days (slow memory)
    
    # Weight bounds
    WEIGHT_MIN = 0.5
    WEIGHT_MAX = 2.0
    
    # Importance bleed factor (α)
    IMPORTANCE_BLEED_ALPHA = 0.2
    
    def __init__(self, supabase_client):
        """
        Initialize coefficient updater.
        
        Args:
            supabase_client: Supabase client for database operations
        """
        self.sb = supabase_client
        self.bucket_vocab = BucketVocabulary()
    
    def calculate_decay_weight(self, trade_timestamp: datetime, current_timestamp: datetime, tau: float) -> float:
        """
        Calculate exponential decay weight for a trade.
        
        Args:
            trade_timestamp: Timestamp of the closed trade
            current_timestamp: Current timestamp
            tau: Time constant in days
            
        Returns:
            Decay weight (0.0 to 1.0)
        """
        delta_t = (current_timestamp - trade_timestamp).total_seconds() / (24 * 3600)  # Convert to days
        if delta_t < 0:
            delta_t = 0  # Handle future timestamps
        
        weight = math.exp(-delta_t / tau)
        return weight
    
    def update_coefficient_ewma(
        self,
        module: str,
        scope: str,
        name: str,
        key: str,
        rr_value: float,
        trade_timestamp: datetime,
        current_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Update a coefficient using EWMA with temporal decay.
        
        Args:
            module: Module identifier ('dm', 'pm', etc.)
            scope: Scope ('lever', 'interaction', 'timeframe')
            name: Lever name ('curator', 'chain', 'cap', etc.)
            key: Bucket value or hashed combination
            rr_value: R/R value from closed trade
            trade_timestamp: Timestamp of the closed trade
            current_timestamp: Current timestamp (defaults to now)
            
        Returns:
            Dictionary with updated coefficient values
        """
        if current_timestamp is None:
            current_timestamp = datetime.now(timezone.utc)
        
        # Get existing coefficient
        existing = (
            self.sb.table("learning_coefficients")
            .select("*")
            .eq("module", module)
            .eq("scope", scope)
            .eq("name", name)
            .eq("key", key)
            .limit(1)
            .execute()
        ).data
        
        # Calculate decay weights
        w_short = self.calculate_decay_weight(trade_timestamp, current_timestamp, self.TAU_SHORT)
        w_long = self.calculate_decay_weight(trade_timestamp, current_timestamp, self.TAU_LONG)
        
        if existing and len(existing) > 0:
            # Update existing coefficient using EWMA
            current = existing[0]
            current_rr_short = current.get('rr_short') or 1.0
            current_rr_long = current.get('rr_long') or 1.0
            current_n = current.get('n', 0)
            
            # EWMA update: new_rr = (1 - α) * old_rr + α * new_rr
            # where α = decay_weight (higher weight for recent trades)
            alpha_short = w_short / (w_short + 1.0)  # Normalize to [0, 0.5] range
            alpha_long = w_long / (w_long + 1.0)
            
            new_rr_short = (1 - alpha_short) * current_rr_short + alpha_short * rr_value
            new_rr_long = (1 - alpha_long) * current_rr_long + alpha_long * rr_value
            new_n = current_n + 1
            
            # Get global R/R for weight calculation
            global_rr_short = self._get_global_rr_short()
            if global_rr_short and global_rr_short > 0:
                new_weight = max(self.WEIGHT_MIN, min(self.WEIGHT_MAX, new_rr_short / global_rr_short))
            else:
                new_weight = 1.0
            
            # Update coefficient
            self.sb.table("learning_coefficients").update({
                "weight": new_weight,
                "rr_short": new_rr_short,
                "rr_long": new_rr_long,
                "n": new_n,
                "updated_at": current_timestamp.isoformat()
            }).eq("module", module).eq("scope", scope).eq("name", name).eq("key", key).execute()
            
            return {
                "weight": new_weight,
                "rr_short": new_rr_short,
                "rr_long": new_rr_long,
                "n": new_n
            }
        else:
            # Create new coefficient
            global_rr_short = self._get_global_rr_short()
            if global_rr_short and global_rr_short > 0:
                initial_weight = max(self.WEIGHT_MIN, min(self.WEIGHT_MAX, rr_value / global_rr_short))
            else:
                initial_weight = 1.0
            
            self.sb.table("learning_coefficients").insert({
                "module": module,
                "scope": scope,
                "name": name,
                "key": key,
                "weight": initial_weight,
                "rr_short": rr_value,
                "rr_long": rr_value,
                "n": 1,
                "updated_at": current_timestamp.isoformat()
            }).execute()
            
            return {
                "weight": initial_weight,
                "rr_short": rr_value,
                "rr_long": rr_value,
                "n": 1
            }
    
    def generate_interaction_key(self, entry_context: Dict[str, Any]) -> str:
        """
        Generate interaction pattern key from entry context.
        
        Creates a hashed combination of lever values for interaction pattern matching.
        
        Args:
            entry_context: Lever values at entry
            
        Returns:
            Interaction key string (e.g., "curator=detweiler|chain=base|age<7d|vol>250k")
        """
        parts = []
        
        # Include all relevant levers
        if entry_context.get('curator'):
            parts.append(f"curator={entry_context['curator']}")
        if entry_context.get('chain'):
            parts.append(f"chain={entry_context['chain']}")
        if entry_context.get('mcap_bucket'):
            parts.append(f"cap={entry_context['mcap_bucket']}")
        if entry_context.get('vol_bucket'):
            parts.append(f"vol={entry_context['vol_bucket']}")
        if entry_context.get('age_bucket'):
            parts.append(f"age={entry_context['age_bucket']}")
        if entry_context.get('intent'):
            parts.append(f"intent={entry_context['intent']}")
        if entry_context.get('mapping_confidence'):
            parts.append(f"conf={entry_context['mapping_confidence']}")
        if entry_context.get('mcap_vol_ratio_bucket'):
            parts.append(f"ratio={entry_context['mcap_vol_ratio_bucket']}")
        
        if not parts:
            return "empty"
        
        # Sort parts for consistent hashing
        parts.sort()
        return "|".join(parts)
    
    def update_interaction_pattern(
        self,
        entry_context: Dict[str, Any],
        rr_value: float,
        trade_timestamp: datetime,
        current_timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update interaction pattern coefficient.
        
        Args:
            entry_context: Lever values at entry
            rr_value: R/R value from closed trade
            trade_timestamp: Timestamp of the closed trade
            current_timestamp: Current timestamp (defaults to now)
            
        Returns:
            Dictionary with updated coefficient values, or None if no interaction pattern
        """
        interaction_key = self.generate_interaction_key(entry_context)
        
        if interaction_key == "empty":
            return None
        
        return self.update_coefficient_ewma(
            module='dm',
            scope='interaction',
            name='interaction',
            key=interaction_key,
            rr_value=rr_value,
            trade_timestamp=trade_timestamp,
            current_timestamp=current_timestamp
        )
    
    def apply_importance_bleed(
        self,
        entry_context: Dict[str, Any],
        interaction_weight: float
    ) -> Dict[str, Tuple[str, float]]:
        """
        Apply importance bleed to overlapping single-factor weights.
        
        When an interaction pattern is active, downweight the single-factor
        coefficients that are part of that interaction to avoid double-counting.
        
        Args:
            entry_context: Lever values at entry
            interaction_weight: Weight of the active interaction pattern
            
        Returns:
            Dictionary mapping lever names to (key, adjusted_weight) tuples
        """
        if interaction_weight == 1.0:
            # No bleed needed if interaction weight is neutral
            return {}
        
        # Only apply bleed if interaction weight is significantly different from 1.0
        if abs(interaction_weight - 1.0) < 0.1:
            return {}
        
        adjusted_weights = {}
        alpha = self.IMPORTANCE_BLEED_ALPHA
        
        # Get single-factor weights for levers in the interaction
        levers = [
            ('curator', entry_context.get('curator')),
            ('chain', entry_context.get('chain')),
            ('cap', entry_context.get('mcap_bucket')),
            ('vol', entry_context.get('vol_bucket')),
            ('age', entry_context.get('age_bucket')),
            ('intent', entry_context.get('intent')),
            ('mapping_confidence', entry_context.get('mapping_confidence')),
        ]
        
        for lever_name, lever_key in levers:
            if not lever_key:
                continue
            
            # Get current single-factor weight
            existing = (
                self.sb.table("learning_coefficients")
                .select("weight")
                .eq("module", "dm")
                .eq("scope", "lever")
                .eq("name", lever_name)
                .eq("key", lever_key)
                .limit(1)
                .execute()
            ).data
            
            if existing and len(existing) > 0:
                current_weight = existing[0].get('weight', 1.0)
                
                # Apply bleed: shrink toward 1.0 by alpha
                # If interaction is strong (weight > 1.0), reduce single-factor weight
                # If interaction is weak (weight < 1.0), reduce single-factor weight toward 1.0
                adjusted_weight = current_weight + alpha * (1.0 - current_weight)
                
                adjusted_weights[lever_name] = (lever_key, adjusted_weight)
        
        return adjusted_weights
    
    def _get_global_rr_short(self) -> Optional[float]:
        """Get global R/R short-term baseline from learning_configs."""
        try:
            result = (
                self.sb.table("learning_configs")
                .select("config_data")
                .eq("module_id", "decision_maker")
                .limit(1)
                .execute()
            ).data
            
            if result and len(result) > 0:
                config_data = result[0].get('config_data', {})
                global_rr = config_data.get('global_rr', {})
                return global_rr.get('rr_short')
            
            return None
        except Exception as e:
            logger.error(f"Error getting global R/R baseline: {e}")
            return None

