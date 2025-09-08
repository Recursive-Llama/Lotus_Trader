"""
Trader Team - Organic Intelligence Trading System

This module contains the Trader Team agents that participate in the organic intelligence
network through execution resonance, uncertainty-driven curiosity, and strategic coordination.

The Trader Team responds to the data-driven heartbeat with specialized execution-focused
analysis that contributes to the organic intelligence network.

Key Components:
- Execution Resonance Integration: φ, ρ, θ calculations for organic evolution
- Execution Uncertainty Handler: Curiosity-driven exploration through uncertainty
- Enhanced Trader Agent Base: Organic CIL influence integration
- Strategic Execution Intelligence: CIL panoramic view integration
- Cross-Team Execution Awareness: Pattern detection across intelligence teams
- Execution Doctrine Integration: Organic knowledge evolution

Architecture:
- Data-driven heartbeat: 1-minute execution response to market data
- Event-driven triggers: Immediate response to Decision Maker approvals
- Fallback intervals: 1-minute if no triggers received
- Organic coordination: Through AD_strands database and resonance
"""

# Core Trader Team Components
from .order_manager import OrderManager
from .performance_analyzer import PerformanceAnalyzer
from .position_tracker import PositionTracker
from .hyperliquid_integration import HyperliquidIntegration
from .venue_fallback_manager import VenueFallbackManager
from .cil_integration import CILIntegration
from .trader_team_coordinator import TraderTeamCoordinator

__all__ = [
    # Core Components
    'OrderManager',
    'PerformanceAnalyzer', 
    'PositionTracker',
    'HyperliquidIntegration',
    'VenueFallbackManager',
    'CILIntegration',
    'TraderTeamCoordinator'
]

__version__ = "1.0.0"
__author__ = "Lotus Trader Team"
__description__ = "Organic Intelligence Trader Team"
