"""
Advanced LLM Components for Central Intelligence Layer

This module contains LLM-first components that provide advanced pattern analysis,
analogy detection, and counterfactual reasoning capabilities for the CIL system.

Components:
- MotifMiner: LLM pattern naming and invariant extraction
- AnalogyEngine: LLM cross-family rhyme detection and transfer hypothesis generation
- CounterfactualCritic: LLM causal probe generation and failure surface analysis
"""

from .motif_miner import MotifMiner, MotifCard
from .analogy_engine import AnalogyEngine, AnalogyPair, TransferCandidate
from .counterfactual_critic import CounterfactualCritic, CounterfactualTest, CausalSkeleton

__all__ = [
    'MotifMiner',
    'MotifCard',
    'AnalogyEngine', 
    'AnalogyPair',
    'TransferCandidate',
    'CounterfactualCritic',
    'CounterfactualTest',
    'CausalSkeleton'
]

