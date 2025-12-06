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
        
        Only timeframe weights are supported (scope='lever', name='timeframe').
        These are stored in learning_configs.config_data.timeframe_weights.
        
        Args:
            module: Module identifier ('dm', 'pm', etc.)
            scope: Must be 'lever'
            name: Must be 'timeframe'
            key: Timeframe key ('1m'|'15m'|'1h'|'4h')
            rr_value: R/R value from closed trade
            trade_timestamp: Timestamp of the closed trade
            current_timestamp: Current timestamp (defaults to now)
            
        Returns:
            Dictionary with updated coefficient values
        """
        if current_timestamp is None:
            current_timestamp = datetime.now(timezone.utc)
        
        # Only timeframe weights are supported
        if scope != 'lever' or name != 'timeframe':
            logger.warning(f"Unsupported coefficient update: scope={scope}, name={name}. Only timeframe weights are supported.")
            return {
                "weight": 1.0,
                "rr_short": rr_value,
                "rr_long": rr_value,
                "n": 0
            }
        
        # Update timeframe weight in learning_configs
        return self._update_timeframe_weight_ewma(module, key, rr_value, trade_timestamp, current_timestamp)
    
    def _update_timeframe_weight_ewma(
        self,
        module: str,
        timeframe: str,
        rr_value: float,
        trade_timestamp: datetime,
        current_timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Update timeframe weight in learning_configs table using EWMA.
        
        Args:
            module: Module identifier ('dm', 'pm', etc.)
            timeframe: Timeframe key ('1m', '15m', '1h', '4h')
            rr_value: R/R value from closed trade
            trade_timestamp: Timestamp of the closed trade
            current_timestamp: Current timestamp
            
        Returns:
            Dictionary with updated coefficient values
        """
        # Map module to module_id for learning_configs
        module_id_map = {
            'dm': 'decision_maker',
            'pm': 'pm',
            'ingest': 'social_ingest'
        }
        module_id = module_id_map.get(module, module)
        
        try:
            # Get existing config
            existing = (
                self.sb.table("learning_configs")
                .select("config_data")
                .eq("module_id", module_id)
                .limit(1)
                .execute()
            ).data
            
            # Calculate decay weights
            w_short = self.calculate_decay_weight(trade_timestamp, current_timestamp, self.TAU_SHORT)
            w_long = self.calculate_decay_weight(trade_timestamp, current_timestamp, self.TAU_LONG)
            
            if existing and len(existing) > 0:
                # Update existing config
                config_data = existing[0].get('config_data', {})
                timeframe_weights = config_data.get('timeframe_weights', {})
                
                # Get existing timeframe data
                tf_data = timeframe_weights.get(timeframe, {})
                current_rr_short = tf_data.get('rr_short', 1.0) if isinstance(tf_data, dict) else 1.0
                current_rr_long = tf_data.get('rr_long', 1.0) if isinstance(tf_data, dict) else 1.0
                current_n = tf_data.get('n', 0) if isinstance(tf_data, dict) else 0
                
                # EWMA update
                alpha_short = w_short / (w_short + 1.0)
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
                
                # Update timeframe weight in config_data
                if 'timeframe_weights' not in config_data:
                    config_data['timeframe_weights'] = {}
                
                config_data['timeframe_weights'][timeframe] = {
                    'weight': new_weight,
                    'rr_short': new_rr_short,
                    'rr_long': new_rr_long,
                    'n': new_n,
                    'updated_at': current_timestamp.isoformat()
                }
                
                # Update learning_configs
                self.sb.table("learning_configs").update({
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system"
                }).eq("module_id", module_id).execute()
                
                logger.debug(f"Updated timeframe weight {timeframe}: weight={new_weight:.3f}, rr_short={new_rr_short:.3f}, n={new_n}")
                
                return {
                    "weight": new_weight,
                    "rr_short": new_rr_short,
                    "rr_long": new_rr_long,
                    "n": new_n
                }
            else:
                # Create new config with timeframe weight
                global_rr_short = self._get_global_rr_short()
                if global_rr_short and global_rr_short > 0:
                    initial_weight = max(self.WEIGHT_MIN, min(self.WEIGHT_MAX, rr_value / global_rr_short))
                else:
                    initial_weight = 1.0
                
                config_data = {
                    'timeframe_weights': {
                        timeframe: {
                            'weight': initial_weight,
                            'rr_short': rr_value,
                            'rr_long': rr_value,
                            'n': 1,
                            'updated_at': current_timestamp.isoformat()
                        }
                    }
                }
                
                self.sb.table("learning_configs").insert({
                    "module_id": module_id,
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system"
                }).execute()
                
                logger.debug(f"Created new timeframe weight {timeframe}: weight={initial_weight:.3f}, n=1")
                
                return {
                    "weight": initial_weight,
                    "rr_short": rr_value,
                    "rr_long": rr_value,
                    "n": 1
                }
        except Exception as e:
            logger.error(f"Error updating timeframe weight in learning_configs: {e}")
            return {
                "weight": 1.0,
                "rr_short": rr_value,
                "rr_long": rr_value,
                "n": 0
            }
    
    
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

