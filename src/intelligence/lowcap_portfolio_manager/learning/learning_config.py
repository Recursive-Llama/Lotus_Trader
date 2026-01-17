"""
Learning System Configuration

Centralized configuration for all learning system parameters.
Allows runtime tuning without code changes via learning_configs table.

Usage:
    from .learning_config import get_learning_config
    config = get_learning_config(sb_client)
    n_min = config.N_MIN
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from supabase import Client

logger = logging.getLogger(__name__)


@dataclass
class LearningConfig:
    """
    Learning System configuration with defaults.
    
    All values can be overridden via learning_configs table.
    """
    
    # Sample thresholds
    N_MIN: int = 12                  # Minimum samples to create a lesson
    N_CONFIDENT: int = 124           # Full confidence threshold
    LOOKBACK_DAYS: int = 90          # How far back to look for trajectories
    
    # Learning rates
    ASYMMETRY_RATIO: float = 1.69    # Loss aversion (failures weight more than wins)
    SPECIFICITY_ALPHA: float = 0.5   # Specificity power factor
    
    # Dimension weights for strength mining
    STRENGTH_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "timeframe": 3.0,
        "ticker": 3.0,
        "mcap_bucket": 2.2,
        "bucket_rank_meso_bin": 2.0,
        "age_bucket": 2.0,
        "opp_meso_bin": 1.8,
        "curator": 1.8,
        "vol_bucket": 1.5,
        "riskoff_meso_bin": 1.4,
        "chain": 1.2,
        "mcap_vol_ratio_bucket": 1.2,
        "conf_meso_bin": 1.0,
        "opp_micro_bin": 0.7,
        "conf_micro_bin": 0.7,
        "riskoff_micro_bin": 0.7,
    })
    
    # Dimension weights for tuning mining
    TUNING_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "timeframe": 3.0,
        "ticker": 2.6,
        "riskoff_meso_bin": 2.2,
        "mcap_bucket": 2.0,
        "conf_meso_bin": 1.8,
        "age_bucket": 1.6,
        "bucket_rank_meso_bin": 1.6,
        "chain": 1.2,
        "vol_bucket": 1.2,
        "opp_meso_bin": 1.0,
        "mcap_vol_ratio_bucket": 1.0,
        "riskoff_micro_bin": 1.0,
        "curator": 0.6,
    })
    
    # dirA/dirE deltas per trajectory type
    DELTA_IMMEDIATE_FAILURE: float = -0.02
    DELTA_TRIMMED_WINNER: float = 0.02
    DELTA_CLEAN_WINNER: float = 0.10
    DELTA_SHADOW_TRIMMED: float = 0.03
    DELTA_SHADOW_CLEAN: float = 0.12
    DELTA_TRIM_BUT_LOSS_E: float = 0.05
    
    # Gate tightening deltas
    DELTA_TS_MIN_TIGHTEN: float = 0.05
    DELTA_HALO_TIGHTEN: float = -0.1
    
    # Override application
    OVERRIDE_CLAMP_MIN: float = -0.5
    OVERRIDE_CLAMP_MAX: float = 0.5
    A_VALUE_MIN: float = 0.1
    A_VALUE_MAX: float = 0.9


def get_learning_config(sb_client: Optional[Client] = None) -> LearningConfig:
    """
    Get learning config, optionally loading overrides from database.
    
    Args:
        sb_client: Supabase client. If None, returns defaults.
    
    Returns:
        LearningConfig with any DB overrides applied.
    """
    config = LearningConfig()
    
    if sb_client is None:
        return config
    
    try:
        result = sb_client.table('learning_configs')\
            .select('config_data')\
            .eq('module_id', 'pm')\
            .single()\
            .execute()
        
        if result.data:
            overrides = result.data.get('config_data', {})
            
            # Apply simple value overrides
            if 'N_MIN' in overrides:
                config.N_MIN = int(overrides['N_MIN'])
            if 'N_CONFIDENT' in overrides:
                config.N_CONFIDENT = int(overrides['N_CONFIDENT'])
            if 'LOOKBACK_DAYS' in overrides:
                config.LOOKBACK_DAYS = int(overrides['LOOKBACK_DAYS'])
            if 'ASYMMETRY_RATIO' in overrides:
                config.ASYMMETRY_RATIO = float(overrides['ASYMMETRY_RATIO'])
            if 'SPECIFICITY_ALPHA' in overrides:
                config.SPECIFICITY_ALPHA = float(overrides['SPECIFICITY_ALPHA'])
            
            # Apply weight overrides
            if 'STRENGTH_WEIGHTS' in overrides:
                config.STRENGTH_WEIGHTS.update(overrides['STRENGTH_WEIGHTS'])
            if 'TUNING_WEIGHTS' in overrides:
                config.TUNING_WEIGHTS.update(overrides['TUNING_WEIGHTS'])
            
            logger.debug("Loaded learning config overrides from DB")
    
    except Exception as e:
        logger.warning(f"Failed to load learning config from DB, using defaults: {e}")
    
    return config
