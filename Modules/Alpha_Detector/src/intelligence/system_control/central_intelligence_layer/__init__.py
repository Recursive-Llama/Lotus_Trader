"""
CIL Learning System Package

This package provides CIL-specific learning capabilities that build on the universal learning foundation.
It includes trading-specific clustering, prediction tracking, outcome analysis, and conditional plan management.

Modules:
- cil_clustering: CIL-specific two-tier clustering with trading features
- prediction_tracker: Tracks trading predictions until completion
- outcome_analysis_engine: Analyzes prediction outcomes for learning
- conditional_plan_manager: Manages conditional trading plans and evolution
"""

from .cil_clustering import CILClustering, CILPatternClusterer
from .prediction_tracker import PredictionTracker, PredictionStatus, PredictionOutcome, PredictionData
from .outcome_analysis_engine import OutcomeAnalysisEngine, AnalysisType, AnalysisResult, PredictionOutcome as OutcomeAnalysisPredictionOutcome
from .conditional_plan_manager import ConditionalPlanManager, PlanStatus, PlanType, ConditionalPlan
from .cil_learning_system import CILLearningSystem

__all__ = [
    # CIL Clustering
    'CILClustering',
    'CILPatternClusterer',
    
    # Prediction Tracking
    'PredictionTracker',
    'PredictionStatus',
    'PredictionOutcome',
    'PredictionData',
    
    # Outcome Analysis
    'OutcomeAnalysisEngine',
    'AnalysisType',
    'AnalysisResult',
    'OutcomeAnalysisPredictionOutcome',
    
    # Conditional Plan Management
    'ConditionalPlanManager',
    'PlanStatus',
    'PlanType',
    'ConditionalPlan',
    
    # CIL Learning System
    'CILLearningSystem'
]
