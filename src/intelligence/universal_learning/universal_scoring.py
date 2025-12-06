"""
Universal Scoring System for All Strands

This module provides universal scoring capabilities for all strand types in the system.
It integrates with the module-specific scoring system to calculate persistence, novelty, and surprise scores.

The scoring system is designed to work with the unified learning system where:
- Everything is strands (signals, intelligence, trading_plans, braids, etc.)
- All strands get scored with persistence, novelty, and surprise using Simons' resonance formulas
- Braids get the average score of their source strands
- Module-specific calculations provide accurate, data-driven scores
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import sys
import os

# Add the learning system to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src', 'learning_system'))

logger = logging.getLogger(__name__)


class UniversalScoring:
    """
    Universal scoring system for all strand types
    
    Calculates persistence, novelty, and surprise scores for any strand
    using the module-specific scoring system with Simons' resonance formulas.
    """
    
    def __init__(self, supabase_manager=None):
        """
        Initialize universal scoring system
        
        Args:
            supabase_manager: Database manager for module-specific scoring
        """
        self.logger = logging.getLogger(__name__)
        self.supabase_manager = supabase_manager
        
        # Initialize module-specific scoring if available
        self.module_scoring = None
        if supabase_manager:
            try:
                from .module_specific_scoring import ModuleSpecificScoring
                self.module_scoring = ModuleSpecificScoring()
            except ImportError as e:
                # Module-specific scoring is optional - fail silently
                self.logger.debug(f"Module-specific scoring not available: {e}")
                self.module_scoring = None
    
    def calculate_persistence_score(self, strand: Dict[str, Any]) -> float:
        """
        Calculate persistence score (0-1) using module-specific scoring
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Persistence score between 0.0 and 1.0
        """
        try:
            # Use module-specific scoring if available
            if self.module_scoring:
                # Determine module type from strand
                module_type = self._get_module_type_from_strand(strand)
                if module_type:
                    # Calculate module-specific persistence score
                    persistence, _, _ = self.module_scoring.calculate_module_scores(strand)
                    return persistence
            
            # Fallback to legacy scoring for braids or unknown types
            if strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average score of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('persistence_score', 0.0) for s in source_strands) / len(source_strands)
                return 0.5
            
            # Default fallback
            return strand.get('persistence_score', strand.get('sig_confidence', 0.5))
                
        except Exception as e:
            self.logger.error(f"Error calculating persistence score: {e}")
            return 0.5
    
    def calculate_novelty_score(self, strand: Dict[str, Any]) -> float:
        """
        Calculate novelty score (0-1) using module-specific scoring
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Novelty score between 0.0 and 1.0
        """
        try:
            # Use module-specific scoring if available
            if self.module_scoring:
                # Determine module type from strand
                module_type = self._get_module_type_from_strand(strand)
                if module_type:
                    # Calculate module-specific novelty score
                    _, novelty, _ = self.module_scoring.calculate_module_scores(strand)
                    return novelty
            
            # Fallback to legacy scoring for braids or unknown types
            if strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average score of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('novelty_score', 0.0) for s in source_strands) / len(source_strands)
                return 0.5
            
            # Default fallback
            return strand.get('novelty_score', 0.5)
                
        except Exception as e:
            self.logger.error(f"Error calculating novelty score: {e}")
            return 0.5
    
    def calculate_surprise_rating(self, strand: Dict[str, Any]) -> float:
        """
        Calculate surprise rating (0-1) using module-specific scoring
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Surprise rating between 0.0 and 1.0
        """
        try:
            # Use module-specific scoring if available
            if self.module_scoring:
                # Determine module type from strand
                module_type = self._get_module_type_from_strand(strand)
                if module_type:
                    # Calculate module-specific surprise score
                    _, _, surprise = self.module_scoring.calculate_module_scores(strand)
                    return surprise
            
            # Fallback to legacy scoring for braids or unknown types
            if strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average score of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('surprise_rating', 0.0) for s in source_strands) / len(source_strands)
                return 0.5
            
            # Default fallback
            return strand.get('surprise_rating', 0.5)
                
        except Exception as e:
            self.logger.error(f"Error calculating surprise rating: {e}")
            return 0.5
    
    def _get_module_type_from_strand(self, strand: Dict[str, Any]) -> Optional[str]:
        """
        Determine module type from strand data
        
        Args:
            strand: Strand dictionary
            
        Returns:
            Module type string or None if unknown
        """
        try:
            # Map strand kinds to module types
            kind_to_module = {
                'pattern': 'rdi',
                'prediction_review': 'cil',
                'conditional_trading_plan': 'ctp',
                'trading_decision': 'dm',
                'execution_outcome': 'td',
                'trade_outcome': 'ctp',  # Trade outcomes are used by CTP for learning
                'portfolio_outcome': 'dm'  # Portfolio outcomes are used by DM for learning
            }
            
            strand_kind = strand.get('kind')
            if strand_kind in kind_to_module:
                return kind_to_module[strand_kind]
            
            # Fallback to agent_id mapping
            agent_id = strand.get('agent_id', '')
            if 'raw_data_intelligence' in agent_id:
                return 'rdi'
            elif 'central_intelligence_layer' in agent_id:
                return 'cil'
            elif 'conditional_trading_planner' in agent_id:
                return 'ctp'
            elif 'decision_maker' in agent_id:
                return 'dm'
            elif 'trader' in agent_id:
                return 'td'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error determining module type: {e}")
            return None
    
    def calculate_all_scores(self, strand: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate all three scores for a strand
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Dictionary with persistence_score, novelty_score, and surprise_rating
        """
        return {
            'persistence_score': self.calculate_persistence_score(strand),
            'novelty_score': self.calculate_novelty_score(strand),
            'surprise_rating': self.calculate_surprise_rating(strand)
        }
    
    def update_strand_scores(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a strand with calculated scores
        
        Args:
            strand: Strand dictionary to update
            
        Returns:
            Updated strand dictionary with scores
        """
        scores = self.calculate_all_scores(strand)
        strand.update(scores)
        return strand


# Example usage and testing
if __name__ == "__main__":
    # Test the universal scoring system
    scoring = UniversalScoring()
    
    # Test different strand types
    test_strands = [
        {
            'agent_id': 'raw_data_intelligence',
            'sig_confidence': 0.8,
            'sig_sigma': 0.7,
            'pattern_type': 'divergence',
            'module_intelligence': {'data_quality_score': 0.9}
        },
        {
            'agent_id': 'central_intelligence_layer',
            'confidence': 0.7,
            'doctrine_status': 'affirmed',
            'strategic_meta_type': 'confluence'
        },
        {
            'kind': 'trading_plan',
            'accumulated_score': 0.6,
            'outcome_score': 0.8,
            'regime': 'anomaly'
        },
        {
            'kind': 'braid',
            'source_strands': [
                {'persistence_score': 0.7, 'novelty_score': 0.6, 'surprise_rating': 0.4},
                {'persistence_score': 0.8, 'novelty_score': 0.5, 'surprise_rating': 0.3}
            ]
        }
    ]
    
    for i, strand in enumerate(test_strands):
        print(f"\nTest Strand {i+1}:")
        print(f"Type: {strand.get('agent_id', strand.get('kind', 'unknown'))}")
        scores = scoring.calculate_all_scores(strand)
        print(f"Scores: {scores}")
