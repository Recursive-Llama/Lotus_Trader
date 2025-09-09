"""
Universal Scoring System for All Strands

This module provides universal scoring capabilities for all strand types in the system.
It calculates persistence, novelty, and surprise scores for any strand regardless of its type.

The scoring system is designed to work with the unified learning system where:
- Everything is strands (signals, intelligence, trading_plans, braids, etc.)
- All strands get scored with persistence, novelty, and surprise
- Braids get the average score of their source strands
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class UniversalScoring:
    """
    Universal scoring system for all strand types
    
    Calculates persistence, novelty, and surprise scores for any strand
    based on its type and available data.
    """
    
    def __init__(self):
        """Initialize universal scoring system"""
        self.logger = logging.getLogger(__name__)
    
    def calculate_persistence_score(self, strand: Dict[str, Any]) -> float:
        """
        Calculate persistence score (0-1) - How reliable/consistent is this pattern?
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Persistence score between 0.0 and 1.0
        """
        try:
            # For Raw Data Intelligence strands
            if strand.get('agent_id') == 'raw_data_intelligence':
                confidence = strand.get('sig_confidence', 0.0)
                data_quality = strand.get('module_intelligence', {}).get('data_quality_score', 1.0)
                return (confidence + data_quality) / 2
            
            # For CIL strands  
            elif strand.get('agent_id') == 'central_intelligence_layer':
                doctrine_status = strand.get('doctrine_status', 'provisional')
                confidence = strand.get('confidence', 0.0)
                
                doctrine_multiplier = {
                    'affirmed': 1.0,
                    'provisional': 0.7,
                    'retired': 0.3,
                    'contraindicated': 0.1
                }.get(doctrine_status, 0.5)
                
                return confidence * doctrine_multiplier
            
            # For Trading Plan strands
            elif strand.get('kind') == 'trading_plan':
                accumulated = strand.get('accumulated_score', 0.0)
                outcome = strand.get('outcome_score', 0.0)
                return (accumulated + outcome) / 2
            
            # For Braid strands
            elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average score of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('persistence_score', 0.0) for s in source_strands) / len(source_strands)
                return 0.5
            
            # For Decision Maker strands
            elif strand.get('agent_id') == 'decision_maker':
                confidence = strand.get('confidence', 0.0)
                # Could add decision-specific persistence logic here
                return confidence
            
            # For Trader strands
            elif strand.get('agent_id') == 'trader':
                execution_quality = strand.get('execution_quality', 0.0)
                outcome = strand.get('outcome_score', 0.0)
                return (execution_quality + outcome) / 2
            
            # Default fallback
            else:
                return strand.get('sig_confidence', 0.5)
                
        except Exception as e:
            self.logger.error(f"Error calculating persistence score: {e}")
            return 0.5
    
    def calculate_novelty_score(self, strand: Dict[str, Any]) -> float:
        """
        Calculate novelty score (0-1) - How unique/new is this pattern?
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Novelty score between 0.0 and 1.0
        """
        try:
            # For Raw Data Intelligence strands
            if strand.get('agent_id') == 'raw_data_intelligence':
                pattern_type = strand.get('pattern_type', 'unknown')
                surprise = strand.get('surprise_rating', 0.0)
                
                novel_patterns = ['anomaly', 'divergence', 'correlation_break']
                if pattern_type in novel_patterns:
                    return min(surprise + 0.3, 1.0)
                else:
                    return surprise
            
            # For CIL strands
            elif strand.get('agent_id') == 'central_intelligence_layer':
                meta_type = strand.get('strategic_meta_type', 'unknown')
                experiment_id = strand.get('experiment_id')
                
                if experiment_id:
                    return 0.8  # Experiments are novel
                elif meta_type in ['confluence', 'doctrine']:
                    return 0.6  # Strategic insights are novel
                else:
                    return 0.4
            
            # For Trading Plan strands
            elif strand.get('kind') == 'trading_plan':
                regime = strand.get('regime', 'unknown')
                
                if regime in ['anomaly', 'transition']:
                    return 0.8
                else:
                    return 0.5
            
            # For Braid strands
            elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average novelty score of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('novelty_score', 0.0) for s in source_strands) / len(source_strands)
                return 0.5
            
            # For Decision Maker strands
            elif strand.get('agent_id') == 'decision_maker':
                decision_type = strand.get('decision_type', 'unknown')
                if decision_type in ['experimental', 'breakthrough']:
                    return 0.8
                else:
                    return 0.5
            
            # For Trader strands
            elif strand.get('agent_id') == 'trader':
                venue = strand.get('venue', 'unknown')
                if venue in ['new_venue', 'experimental']:
                    return 0.7
                else:
                    return 0.4
            
            # Default fallback
            else:
                return 0.5
                
        except Exception as e:
            self.logger.error(f"Error calculating novelty score: {e}")
            return 0.5
    
    def calculate_surprise_rating(self, strand: Dict[str, Any]) -> float:
        """
        Calculate surprise rating (0-1) - How unexpected was this outcome?
        
        Args:
            strand: Strand dictionary with all fields
            
        Returns:
            Surprise rating between 0.0 and 1.0
        """
        try:
            # For Raw Data Intelligence strands
            if strand.get('agent_id') == 'raw_data_intelligence':
                sigma = strand.get('sig_sigma', 0.0)
                confidence = strand.get('sig_confidence', 0.0)
                
                # High sigma with low confidence = surprising
                if sigma > 0.8 and confidence < 0.5:
                    return 0.9
                elif sigma > 0.6 and confidence < 0.7:
                    return 0.7
                else:
                    return 0.3
            
            # For CIL strands
            elif strand.get('agent_id') == 'central_intelligence_layer':
                doctrine_status = strand.get('doctrine_status', 'provisional')
                
                if doctrine_status == 'contraindicated':
                    return 0.9  # Very surprising when something is contraindicated
                elif doctrine_status == 'retired':
                    return 0.7  # Surprising when something is retired
                else:
                    return 0.3
            
            # For Trading Plan strands
            elif strand.get('kind') == 'trading_plan':
                prediction = strand.get('prediction_score', 0.0)
                outcome = strand.get('outcome_score', 0.0)
                
                # High prediction with low outcome = surprising
                if prediction > 0.8 and outcome < 0.3:
                    return 0.9
                elif prediction > 0.6 and outcome < 0.5:
                    return 0.7
                else:
                    return 0.3
            
            # For Braid strands
            elif strand.get('kind') in ['braid', 'meta_braid', 'meta2_braid']:
                # Braids get the average surprise rating of their source strands
                source_strands = strand.get('source_strands', [])
                if source_strands:
                    return sum(s.get('surprise_rating', 0.0) for s in source_strands) / len(source_strands)
                return 0.3
            
            # For Decision Maker strands
            elif strand.get('agent_id') == 'decision_maker':
                risk_level = strand.get('risk_level', 'medium')
                outcome = strand.get('outcome_score', 0.0)
                
                if risk_level == 'high' and outcome > 0.8:
                    return 0.8  # Surprising when high risk pays off
                elif risk_level == 'low' and outcome < 0.3:
                    return 0.7  # Surprising when low risk fails
                else:
                    return 0.3
            
            # For Trader strands
            elif strand.get('agent_id') == 'trader':
                slippage = strand.get('slippage', 0.0)
                expected_slippage = strand.get('expected_slippage', 0.0)
                
                if slippage > expected_slippage * 2:
                    return 0.8  # Surprising when slippage is much higher than expected
                else:
                    return 0.3
            
            # Default fallback
            else:
                return 0.3
                
        except Exception as e:
            self.logger.error(f"Error calculating surprise rating: {e}")
            return 0.3
    
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
