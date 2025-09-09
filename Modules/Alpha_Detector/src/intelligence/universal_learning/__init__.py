"""
Universal Learning System

This module provides the foundation learning system that works with all strand types.
It implements universal scoring, clustering, and learning capabilities.

Components:
- UniversalScoring: Calculates persistence, novelty, and surprise scores for all strands
- UniversalClustering: Implements two-tier clustering (column + pattern)
- UniversalLearningSystem: Main system that integrates scoring and clustering

This is the foundation that CIL specialized learning builds upon.
"""

from .universal_scoring import UniversalScoring
from .universal_clustering import UniversalClustering, Cluster
from .universal_learning_system import UniversalLearningSystem

__all__ = [
    'UniversalScoring',
    'UniversalClustering', 
    'Cluster',
    'UniversalLearningSystem'
]
