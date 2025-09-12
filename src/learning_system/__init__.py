"""
Centralized Learning System

A standalone, database-driven learning module that processes ANY strand type
to create intelligent braids. Eliminates duplicate learning systems and provides
a unified, flexible learning infrastructure for all modules.

Key Features:
- Processes any strand type (pattern, prediction_review, trade_outcome, etc.)
- Database-driven learning via triggers
- Centralized prompt management
- Flexible configuration per strand type
- Automated braid creation (level 2+)

Architecture:
- Strand Processor: Identifies strand type and learning requirements
- Multi-Cluster Grouping Engine: Groups strands into 7 cluster types
- Per-Cluster Learning System: Independent learning per cluster
- LLM Learning Analyzer: Task-specific LLM analysis
- Braid Level Manager: Creates braids at appropriate level
"""

from .strand_processor import StrandProcessor
from .learning_pipeline import LearningPipeline
from .centralized_learning_system import CentralizedLearningSystem
from .mathematical_resonance_engine import MathematicalResonanceEngine

__all__ = [
    'StrandProcessor',
    'LearningPipeline', 
    'CentralizedLearningSystem',
    'MathematicalResonanceEngine'
]
