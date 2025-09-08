"""
Trading Plans Package
Phase 1.4: Trading Plan Generation System
"""

from .models import (
    TradingPlan, SignalPack, RiskMetrics, ExecutionParameters, MarketContext,
    generate_plan_id, generate_pack_id, calculate_time_horizon, calculate_valid_until
)
from .config import TradingPlanConfig, get_config, reload_config
from .trading_plan_builder import TradingPlanBuilder
from .signal_pack_generator import SignalPackGenerator

__all__ = [
    # Models
    'TradingPlan',
    'SignalPack', 
    'RiskMetrics',
    'ExecutionParameters',
    'MarketContext',
    'generate_plan_id',
    'generate_pack_id',
    'calculate_time_horizon',
    'calculate_valid_until',
    
    # Configuration
    'TradingPlanConfig',
    'get_config',
    'reload_config',
    
    # Core Components
    'TradingPlanBuilder',
    'SignalPackGenerator'
]

__version__ = '1.0.0'
__author__ = 'Lotus Trader Alpha Detector'
__description__ = 'Trading Plan Generation System for Alpha Detector Module'

