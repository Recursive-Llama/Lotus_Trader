"""
Central Intelligence Layer (CIL) - Simplified

Simplified CIL with 5 core components:
1. Prediction Engine - Main prediction creation and tracking
2. Learning System - Continuous learning from predictions  
3. Prediction Tracker - Track all predictions and outcomes
4. Outcome Analysis - Analyze completed predictions
5. Conditional Plan Manager - Create trading plans from confident patterns

Advanced CIL components have been moved to advanced_cil module.
"""

from .simplified_cil import SimplifiedCIL
from .prediction_engine import PredictionEngine, PatternGroupingSystem, PredictionTracker

__all__ = [
    'SimplifiedCIL',
    'PredictionEngine', 
    'PatternGroupingSystem',
    'PredictionTracker'
]

__version__ = "2.0.0"
__author__ = "Lotus Trader Team"
