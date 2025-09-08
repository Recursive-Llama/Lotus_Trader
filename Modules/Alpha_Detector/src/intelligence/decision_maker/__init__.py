"""
Decision Maker Intelligence Module

This module provides intelligence for risk management and trading plan evaluation,
integrating with the Central Intelligence Layer (CIL) through organic influence.
It includes:

- Risk assessment and portfolio optimization
- Trading plan evaluation and approval
- Compliance monitoring and risk management
- Cross-team risk pattern awareness
- Strategic risk intelligence contribution
"""

# Phase 1 Components (Implemented)
from .enhanced_decision_agent_base import EnhancedDecisionMakerAgent
from .risk_resonance_integration import RiskResonanceIntegration
from .risk_uncertainty_handler import RiskUncertaintyHandler

# Phase 2 Components (Implemented)
from .risk_motif_integration import RiskMotifIntegration
from .strategic_risk_insight_consumer import StrategicRiskInsightConsumer
from .cross_team_risk_integration import CrossTeamRiskIntegration

# Phase 3 Components (Implemented)
from .risk_doctrine_integration import RiskDoctrineIntegration
from .enhanced_risk_assessment_agent import EnhancedRiskAssessmentAgent

# New Components - CIL Integration and Portfolio Data
from .decision_maker_strand_listener import DecisionMakerStrandListener
from .portfolio_data_integration import PortfolioDataIntegration

__all__ = [
    # Phase 1 Components
    'EnhancedDecisionMakerAgent',
    'RiskResonanceIntegration',
    'RiskUncertaintyHandler',
    
    # Phase 2 Components
    'RiskMotifIntegration',
    'StrategicRiskInsightConsumer',
    'CrossTeamRiskIntegration',
    
    # Phase 3 Components
    'RiskDoctrineIntegration',
    'EnhancedRiskAssessmentAgent',
    
    # New Components - CIL Integration and Portfolio Data
    'DecisionMakerStrandListener',
    'PortfolioDataIntegration'
]
