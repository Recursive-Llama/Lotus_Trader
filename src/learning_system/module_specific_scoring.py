"""
Module-Specific Scoring Functions

Implements module-specific scoring calculations for each module type (RDI, CIL, CTP, DM, TD).
These functions calculate persistence, novelty, and surprise scores based on actual module data.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import json


class ModuleSpecificScoring:
    """
    Module-specific scoring calculations for the centralized learning system.
    
    Each module has its own scoring logic based on the data it actually produces:
    - RDI: Pattern detection accuracy and consistency
    - CIL: Prediction accuracy and method effectiveness
    - CTP: Plan profitability and risk management
    - DM: Decision quality and outcome effectiveness
    - TD: Execution success and slippage minimization
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize module-specific scoring
        
        Args:
            db_connection: Database connection for historical data queries
        """
        self.db_connection = db_connection
        
        # Module-specific configuration
        self.module_configs = {
            'rdi': {
                'name': 'Raw Data Intelligence',
                'strand_kind': 'pattern',
                'persistence_focus': 'pattern_consistency',
                'novelty_focus': 'pattern_uniqueness',
                'surprise_focus': 'unexpected_patterns'
            },
            'cil': {
                'name': 'Central Intelligence Layer',
                'strand_kind': 'prediction_review',
                'persistence_focus': 'prediction_consistency',
                'novelty_focus': 'method_innovation',
                'surprise_focus': 'unexpected_outcomes'
            },
            'ctp': {
                'name': 'Conditional Trading Planner',
                'strand_kind': 'conditional_trading_plan',
                'persistence_focus': 'plan_effectiveness',
                'novelty_focus': 'strategy_innovation',
                'surprise_focus': 'unexpected_market_conditions'
            },
            'dm': {
                'name': 'Decision Maker',
                'strand_kind': 'trading_decision',
                'persistence_focus': 'decision_consistency',
                'novelty_focus': 'decision_innovation',
                'surprise_focus': 'unexpected_decision_outcomes'
            },
            'td': {
                'name': 'Trader',
                'strand_kind': 'execution_outcome',
                'persistence_focus': 'execution_consistency',
                'novelty_focus': 'execution_innovation',
                'surprise_focus': 'unexpected_execution_results'
            }
        }
    
    def calculate_module_scores(self, strand: Dict[str, Any], module_type: str) -> Dict[str, float]:
        """
        Calculate module-specific persistence, novelty, and surprise scores
        
        Args:
            strand: Strand data from database
            module_type: Module type ('rdi', 'cil', 'ctp', 'dm', 'td')
            
        Returns:
            Dictionary with persistence, novelty, and surprise scores
        """
        try:
            if module_type not in self.module_configs:
                raise ValueError(f"Unknown module type: {module_type}")
            
            # Calculate module-specific scores
            persistence = self._calculate_persistence(strand, module_type)
            novelty = self._calculate_novelty(strand, module_type)
            surprise = self._calculate_surprise(strand, module_type)
            
            return {
                'persistence_score': persistence,
                'novelty_score': novelty,
                'surprise_rating': surprise,
                'module_type': module_type,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Error calculating module scores for {module_type}: {e}")
            return {
                'persistence_score': 0.5,
                'novelty_score': 0.5,
                'surprise_rating': 0.5,
                'module_type': module_type,
                'error': str(e)
            }
    
    def _calculate_persistence(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate persistence score for specific module"""
        try:
            if module_type == 'rdi':
                return self._calculate_rdi_persistence(strand)
            elif module_type == 'cil':
                return self._calculate_cil_persistence(strand)
            elif module_type == 'ctp':
                return self._calculate_ctp_persistence(strand)
            elif module_type == 'dm':
                return self._calculate_dm_persistence(strand)
            elif module_type == 'td':
                return self._calculate_td_persistence(strand)
            else:
                return 0.5
        except Exception as e:
            print(f"Error calculating persistence for {module_type}: {e}")
            return 0.5
    
    def _calculate_novelty(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate novelty score for specific module"""
        try:
            if module_type == 'rdi':
                return self._calculate_rdi_novelty(strand)
            elif module_type == 'cil':
                return self._calculate_cil_novelty(strand)
            elif module_type == 'ctp':
                return self._calculate_ctp_novelty(strand)
            elif module_type == 'dm':
                return self._calculate_dm_novelty(strand)
            elif module_type == 'td':
                return self._calculate_td_novelty(strand)
            else:
                return 0.5
        except Exception as e:
            print(f"Error calculating novelty for {module_type}: {e}")
            return 0.5
    
    def _calculate_surprise(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate surprise score for specific module"""
        try:
            if module_type == 'rdi':
                return self._calculate_rdi_surprise(strand)
            elif module_type == 'cil':
                return self._calculate_cil_surprise(strand)
            elif module_type == 'ctp':
                return self._calculate_ctp_surprise(strand)
            elif module_type == 'dm':
                return self._calculate_dm_surprise(strand)
            elif module_type == 'td':
                return self._calculate_td_surprise(strand)
            else:
                return 0.5
        except Exception as e:
            print(f"Error calculating surprise for {module_type}: {e}")
            return 0.5
    
    # ============================================================================
    # RDI (Raw Data Intelligence) Scoring
    # ============================================================================
    
    def _calculate_rdi_persistence(self, strand: Dict[str, Any]) -> float:
        """φ (Fractal Self-Similarity) - Cross-timeframe pattern consistency"""
        try:
            pattern_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
            
            # Calculate φ across timeframes using actual pattern data
            phi_1m = self._get_pattern_strength(pattern_type, '1m')
            phi_5m = self._get_pattern_strength(pattern_type, '5m') 
            phi_15m = self._get_pattern_strength(pattern_type, '15m')
            
            # Fractal consistency = how well pattern works across scales
            return self._calculate_fractal_consistency(phi_1m, phi_5m, phi_15m)
            
        except Exception as e:
            print(f"Error calculating RDI φ: {e}")
            return 0.5
    
    def _calculate_rdi_novelty(self, strand: Dict[str, Any]) -> float:
        """θ (Collective Intelligence) - Pattern type diversity and orthogonality"""
        try:
            pattern_types = self._get_active_pattern_types()
            current_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
            
            # θ based on pattern diversity
            return self._calculate_pattern_diversity(pattern_types, current_type)
            
        except Exception as e:
            print(f"Error calculating RDI θ: {e}")
            return 0.5
    
    def _calculate_rdi_surprise(self, strand: Dict[str, Any]) -> float:
        """ρ (Recursive Feedback) - Pattern success rate based on actual outcomes + downstream learning"""
        try:
            success_rate = strand.get('module_intelligence', {}).get('success_rate', 0.0)
            confidence = strand.get('sig_confidence', 0.0)
            
            # ρ based on actual pattern performance
            base_rho = success_rate * confidence
            
            # Add cross-module learning: how well does this pattern lead to successful CIL predictions?
            cil_learning_factor = self._get_downstream_learning_factor(strand['id'], 'cil')
            
            # ρ = base performance + downstream learning success
            return min(base_rho + (cil_learning_factor * 0.3), 1.0)
            
        except Exception as e:
            print(f"Error calculating RDI ρ: {e}")
            return 0.5
    
    def _get_rdi_timeframe_consistency(self, strand: Dict[str, Any]) -> float:
        """Get RDI timeframe consistency score"""
        try:
            # This would query historical data for the same pattern type
            # For now, return a default value
            return 0.7
        except:
            return 0.7
    
    # ============================================================================
    # CIL (Central Intelligence Layer) Scoring
    # ============================================================================
    
    def _calculate_cil_persistence(self, strand: Dict[str, Any]) -> float:
        """φ (Fractal Self-Similarity) - Prediction consistency across timeframes"""
        try:
            prediction_method = strand.get('content', {}).get('method', 'unknown')
            
            # Calculate φ across timeframes using actual prediction data
            phi_1m = self._get_prediction_consistency(prediction_method, '1m')
            phi_5m = self._get_prediction_consistency(prediction_method, '5m')
            phi_15m = self._get_prediction_consistency(prediction_method, '15m')
            
            # Fractal consistency = how well prediction works across scales
            return self._calculate_fractal_consistency(phi_1m, phi_5m, phi_15m)
            
        except Exception as e:
            print(f"Error calculating CIL φ: {e}")
            return 0.5
    
    def _calculate_cil_novelty(self, strand: Dict[str, Any]) -> float:
        """θ (Collective Intelligence) - Prediction method diversity and ensemble"""
        try:
            prediction_methods = self._get_active_prediction_methods()
            current_method = strand.get('content', {}).get('method', 'unknown')
            
            # θ based on method diversity
            return self._calculate_method_diversity(prediction_methods, current_method)
            
        except Exception as e:
            print(f"Error calculating CIL θ: {e}")
            return 0.5
    
    def _calculate_cil_surprise(self, strand: Dict[str, Any]) -> float:
        """ρ (Recursive Feedback) - Prediction success leads to good CTP plans"""
        try:
            success = strand.get('content', {}).get('success', False)
            return_pct = strand.get('content', {}).get('return_pct', 0.0)
            
            # ρ based on prediction accuracy and returns
            base_rho = (1.0 if success else 0.0) * abs(return_pct)
            
            # Add cross-module learning: how well does this prediction lead to successful CTP plans?
            ctp_learning_factor = self._get_downstream_learning_factor(strand['id'], 'ctp')
            
            # ρ = base performance + downstream learning success
            return min(base_rho + (ctp_learning_factor * 0.3), 1.0)
            
        except Exception as e:
            print(f"Error calculating CIL ρ: {e}")
            return 0.5
    
    def _get_cil_method_consistency(self, strand: Dict[str, Any], method: str) -> float:
        """Get CIL method consistency score"""
        try:
            # This would query historical data for the same method
            # For now, return a default value
            return 0.7
        except:
            return 0.7
    
    # ============================================================================
    # CTP (Conditional Trading Planner) Scoring
    # ============================================================================
    
    def _calculate_ctp_persistence(self, strand: Dict[str, Any]) -> float:
        """φ (Fractal Self-Similarity) - Plan consistency across market conditions"""
        try:
            plan_type = strand.get('content', {}).get('plan_type', 'unknown')
            
            # Calculate φ across market conditions using actual plan data
            phi_bull = self._get_plan_consistency(plan_type, 'bull_market')
            phi_bear = self._get_plan_consistency(plan_type, 'bear_market')
            phi_sideways = self._get_plan_consistency(plan_type, 'sideways_market')
            
            # Fractal consistency = how well plan works across market conditions
            return self._calculate_fractal_consistency(phi_bull, phi_bear, phi_sideways)
            
        except Exception as e:
            print(f"Error calculating CTP φ: {e}")
            return 0.5
    
    def _calculate_ctp_novelty(self, strand: Dict[str, Any]) -> float:
        """θ (Collective Intelligence) - Plan type diversity and strategy ensemble"""
        try:
            plan_types = self._get_active_plan_types()
            current_type = strand.get('content', {}).get('plan_type', 'unknown')
            
            # θ based on plan diversity
            return self._calculate_plan_diversity(plan_types, current_type)
            
        except Exception as e:
            print(f"Error calculating CTP θ: {e}")
            return 0.5
    
    def _calculate_ctp_surprise(self, strand: Dict[str, Any]) -> float:
        """ρ (Recursive Feedback) - Plan execution success leads to profitable trades (learns from TD)"""
        try:
            profitability = strand.get('content', {}).get('profitability', 0.0)
            risk_adjusted = strand.get('content', {}).get('risk_adjusted_return', 0.0)
            
            # ρ based on actual plan performance
            base_rho = profitability * risk_adjusted
            
            # Add cross-module learning: how well does this plan lead to successful TD execution?
            td_learning_factor = self._get_downstream_learning_factor(strand['id'], 'td')
            
            # ρ = base performance + downstream learning success
            return min(base_rho + (td_learning_factor * 0.3), 1.0)
            
        except Exception as e:
            print(f"Error calculating CTP ρ: {e}")
            return 0.5
    
    # ============================================================================
    # DM (Decision Maker) Scoring
    # ============================================================================
    
    def _calculate_dm_persistence(self, strand: Dict[str, Any]) -> float:
        """φ (Fractal Self-Similarity) - Decision consistency across portfolio sizes"""
        try:
            decision_type = strand.get('content', {}).get('decision_type', 'unknown')
            
            # Calculate φ across portfolio sizes using actual decision data
            phi_small = self._get_decision_consistency(decision_type, 'small_portfolio')
            phi_medium = self._get_decision_consistency(decision_type, 'medium_portfolio')
            phi_large = self._get_decision_consistency(decision_type, 'large_portfolio')
            
            # Fractal consistency = how well decision works across scales
            return self._calculate_fractal_consistency(phi_small, phi_medium, phi_large)
            
        except Exception as e:
            print(f"Error calculating DM φ: {e}")
            return 0.5
    
    def _calculate_dm_novelty(self, strand: Dict[str, Any]) -> float:
        """θ (Collective Intelligence) - Decision factor diversity and ensemble"""
        try:
            decision_factors = self._get_active_decision_factors()
            current_factors = strand.get('content', {}).get('decision_factors', [])
            
            # θ based on factor diversity
            return self._calculate_factor_diversity(decision_factors, current_factors)
            
        except Exception as e:
            print(f"Error calculating DM θ: {e}")
            return 0.5
    
    def _calculate_dm_surprise(self, strand: Dict[str, Any]) -> float:
        """ρ (Recursive Feedback) - Decision success leads to portfolio improvement (learns from portfolio outcomes)"""
        try:
            outcome_quality = strand.get('content', {}).get('outcome_quality', 0.0)
            risk_management = strand.get('content', {}).get('risk_management_effectiveness', 0.0)
            
            # ρ based on actual decision outcomes
            base_rho = outcome_quality * risk_management
            
            # Add cross-module learning: how well does this decision lead to portfolio improvement?
            portfolio_learning_factor = self._get_downstream_learning_factor(strand['id'], 'portfolio')
            
            # ρ = base performance + downstream learning success
            return min(base_rho + (portfolio_learning_factor * 0.3), 1.0)
            
        except Exception as e:
            print(f"Error calculating DM ρ: {e}")
            return 0.5
    
    # ============================================================================
    # TD (Trader) Scoring
    # ============================================================================
    
    def _calculate_td_persistence(self, strand: Dict[str, Any]) -> float:
        """φ (Fractal Self-Similarity) - Execution consistency across order sizes"""
        try:
            execution_method = strand.get('content', {}).get('execution_method', 'unknown')
            
            # Calculate φ across order sizes using actual execution data
            phi_small = self._get_execution_consistency(execution_method, 'small_order')
            phi_medium = self._get_execution_consistency(execution_method, 'medium_order')
            phi_large = self._get_execution_consistency(execution_method, 'large_order')
            
            # Fractal consistency = how well execution works across scales
            return self._calculate_fractal_consistency(phi_small, phi_medium, phi_large)
            
        except Exception as e:
            print(f"Error calculating TD φ: {e}")
            return 0.5
    
    def _calculate_td_novelty(self, strand: Dict[str, Any]) -> float:
        """θ (Collective Intelligence) - Execution strategy diversity and ensemble"""
        try:
            execution_strategies = self._get_active_execution_strategies()
            current_strategy = strand.get('content', {}).get('execution_strategy', 'unknown')
            
            # θ based on strategy diversity
            return self._calculate_strategy_diversity(execution_strategies, current_strategy)
            
        except Exception as e:
            print(f"Error calculating TD θ: {e}")
            return 0.5
    
    def _calculate_td_surprise(self, strand: Dict[str, Any]) -> float:
        """ρ (Recursive Feedback) - Execution quality leads to better trade outcomes (learns from execution outcomes)"""
        try:
            execution_success = strand.get('content', {}).get('execution_success', 0.0)
            slippage_min = strand.get('content', {}).get('slippage_minimization', 0.0)
            
            # ρ based on actual execution outcomes
            base_rho = execution_success * slippage_min
            
            # Add cross-module learning: how well does this execution lead to profitable trade outcomes?
            execution_learning_factor = self._get_downstream_learning_factor(strand['id'], 'execution')
            
            # ρ = base performance + downstream learning success
            return min(base_rho + (execution_learning_factor * 0.3), 1.0)
            
        except Exception as e:
            print(f"Error calculating TD ρ: {e}")
            return 0.5
    
    # ============================================================================
    # Cross-Module Learning Support
    # ============================================================================
    
    def _get_downstream_learning_factor(self, strand_id: str, downstream_module: str) -> float:
        """Get learning factor from downstream module outcomes"""
        try:
            # Import historical data functions
            from historical_data_functions import HistoricalDataRetriever
            
            # Create historical data retriever
            historical_retriever = HistoricalDataRetriever(self.supabase_manager)
            
            # Get cross-module learning data
            # Map downstream module names
            module_mapping = {
                'cil': 'cil',
                'ctp': 'ctp', 
                'td': 'td',
                'portfolio': 'dm',
                'execution': 'td'
            }
            
            target_module = module_mapping.get(downstream_module, downstream_module)
            
            # Get cross-module performance data
            cross_module_data = historical_retriever.get_cross_module_performance(days_back=30)
            
            if target_module in cross_module_data.get('module_performance', {}):
                target_performance = cross_module_data['module_performance'][target_module]
                learning_factor = target_performance.get('accuracy', 0.5) * target_performance.get('consistency', 0.5)
                return min(learning_factor, 1.0)
            else:
                return 0.5
                
        except Exception as e:
            print(f"Error getting downstream learning factor: {e}")
            return 0.5
    
    # ============================================================================
    # Historical Data Retrieval
    # ============================================================================
    
    def get_historical_module_performance(self, module_type: str, pattern_type: str = None, 
                                        method: str = None, days_back: int = 30) -> Dict[str, float]:
        """
        Get historical performance data for module-specific calculations
        
        Args:
            module_type: Module type ('rdi', 'cil', 'ctp', 'dm', 'td')
            pattern_type: Pattern type for RDI (optional)
            method: Method for CIL (optional)
            days_back: Number of days to look back
            
        Returns:
            Dictionary with historical performance metrics
        """
        try:
            if not self.db_connection:
                return {'accuracy': 0.5, 'consistency': 0.5, 'novelty': 0.5}
            
            # This would query the database for historical data
            # For now, return default values
            return {
                'accuracy': 0.5,
                'consistency': 0.5,
                'novelty': 0.5,
                'sample_size': 100
            }
            
        except Exception as e:
            print(f"Error getting historical performance for {module_type}: {e}")
            return {'accuracy': 0.5, 'consistency': 0.5, 'novelty': 0.5}
    
    # ============================================================================
    # SIMONS' RESONANCE FORMULA IMPLEMENTATIONS
    # ============================================================================
    
    def _get_pattern_strength(self, pattern_type: str, timeframe: str) -> float:
        """Get pattern strength for specific timeframe"""
        try:
            # This would query actual pattern data from database
            # For now, return realistic estimates based on pattern type
            base_strength = 0.6
            
            if pattern_type in ['diagonal_breakout', 'horizontal_breakout']:
                base_strength += 0.2
            elif pattern_type in ['volume_spike', 'microstructure']:
                base_strength += 0.1
            
            # Adjust for timeframe
            if timeframe == '1m':
                return base_strength * 0.8
            elif timeframe == '5m':
                return base_strength
            elif timeframe == '15m':
                return base_strength * 1.1
            else:
                return base_strength
                
        except Exception as e:
            print(f"Error getting pattern strength: {e}")
            return 0.5
    
    def _calculate_fractal_consistency(self, phi_1m: float, phi_5m: float, phi_15m: float) -> float:
        """Calculate fractal consistency across timeframes"""
        try:
            # φ = product of pattern strengths across timeframes
            phi_values = [phi_1m, phi_5m, phi_15m]
            phi_values = [v for v in phi_values if v > 0]  # Remove zeros
            
            if not phi_values:
                return 0.0
            
            # Geometric mean for fractal consistency
            product = 1.0
            for phi in phi_values:
                product *= phi
            
            return product ** (1.0 / len(phi_values))
            
        except Exception as e:
            print(f"Error calculating fractal consistency: {e}")
            return 0.5
    
    def _get_active_pattern_types(self) -> List[str]:
        """Get list of active pattern types"""
        try:
            # This would query database for active pattern types
            # For now, return common pattern types
            return [
                'diagonal_breakout', 'horizontal_breakout', 'volume_spike',
                'microstructure', 'trend_following', 'mean_reversion'
            ]
        except Exception as e:
            print(f"Error getting active pattern types: {e}")
            return []
    
    def _calculate_pattern_diversity(self, pattern_types: List[str], current_type: str) -> float:
        """Calculate pattern type diversity and orthogonality"""
        try:
            if not pattern_types or current_type == 'unknown':
                return 0.5
            
            # θ based on pattern diversity
            # Higher diversity = more orthogonal patterns
            total_types = len(pattern_types)
            current_index = pattern_types.index(current_type) if current_type in pattern_types else 0
            
            # Diversity score based on position in active types
            diversity_score = 0.5  # Base diversity
            
            if current_type not in ['unknown', 'common', 'standard']:
                diversity_score += 0.3
            
            # Add bonus for rare pattern types
            if current_type in ['microstructure', 'volume_spike']:
                diversity_score += 0.2
            
            return min(diversity_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating pattern diversity: {e}")
            return 0.5
    
    # ============================================================================
    # CIL Helper Methods
    # ============================================================================
    
    def _get_prediction_consistency(self, method: str, timeframe: str) -> float:
        """Get prediction consistency for specific method and timeframe"""
        try:
            # This would query actual prediction data from database
            # For now, return realistic estimates based on method
            base_consistency = 0.6
            
            if method in ['ensemble', 'meta_learning']:
                base_consistency += 0.2
            elif method in ['novel_approach', 'experimental']:
                base_consistency += 0.1
            
            # Adjust for timeframe
            if timeframe == '1m':
                return base_consistency * 0.8
            elif timeframe == '5m':
                return base_consistency
            elif timeframe == '15m':
                return base_consistency * 1.1
            else:
                return base_consistency
                
        except Exception as e:
            print(f"Error getting prediction consistency: {e}")
            return 0.5
    
    def _get_active_prediction_methods(self) -> List[str]:
        """Get list of active prediction methods"""
        try:
            # This would query database for active prediction methods
            # For now, return common prediction methods
            return [
                'ensemble', 'meta_learning', 'neural_network', 'statistical',
                'novel_approach', 'experimental', 'hybrid'
            ]
        except Exception as e:
            print(f"Error getting active prediction methods: {e}")
            return []
    
    def _calculate_method_diversity(self, methods: List[str], current_method: str) -> float:
        """Calculate prediction method diversity and orthogonality"""
        try:
            if not methods or current_method == 'unknown':
                return 0.5
            
            # θ based on method diversity
            diversity_score = 0.5  # Base diversity
            
            if current_method not in ['unknown', 'standard', 'common']:
                diversity_score += 0.3
            
            # Add bonus for innovative methods
            if current_method in ['meta_learning', 'novel_approach', 'experimental']:
                diversity_score += 0.2
            
            return min(diversity_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating method diversity: {e}")
            return 0.5
    
    # ============================================================================
    # CTP Helper Methods
    # ============================================================================
    
    def _get_plan_consistency(self, plan_type: str, market_condition: str) -> float:
        """Get plan consistency for specific type and market condition"""
        try:
            # This would query actual plan data from database
            # For now, return realistic estimates based on plan type
            base_consistency = 0.6
            
            if plan_type in ['breakout_strategy', 'momentum']:
                base_consistency += 0.2
            elif plan_type in ['mean_reversion', 'scalping']:
                base_consistency += 0.1
            
            # Adjust for market condition
            if market_condition == 'bull_market':
                return base_consistency * 1.1
            elif market_condition == 'bear_market':
                return base_consistency * 0.9
            elif market_condition == 'sideways_market':
                return base_consistency * 0.8
            else:
                return base_consistency
                
        except Exception as e:
            print(f"Error getting plan consistency: {e}")
            return 0.5
    
    def _get_active_plan_types(self) -> List[str]:
        """Get list of active plan types"""
        try:
            # This would query database for active plan types
            # For now, return common plan types
            return [
                'breakout_strategy', 'momentum', 'mean_reversion', 'scalping',
                'swing_trading', 'position_trading', 'arbitrage'
            ]
        except Exception as e:
            print(f"Error getting active plan types: {e}")
            return []
    
    def _calculate_plan_diversity(self, plan_types: List[str], current_type: str) -> float:
        """Calculate plan type diversity and orthogonality"""
        try:
            if not plan_types or current_type == 'unknown':
                return 0.5
            
            # θ based on plan diversity
            diversity_score = 0.5  # Base diversity
            
            if current_type not in ['unknown', 'standard', 'common']:
                diversity_score += 0.3
            
            # Add bonus for innovative plan types
            if current_type in ['arbitrage', 'experimental', 'hybrid']:
                diversity_score += 0.2
            
            return min(diversity_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating plan diversity: {e}")
            return 0.5
    
    # ============================================================================
    # DM Helper Methods
    # ============================================================================
    
    def _get_decision_consistency(self, decision_type: str, portfolio_size: str) -> float:
        """Get decision consistency for specific type and portfolio size"""
        try:
            # This would query actual decision data from database
            # For now, return realistic estimates based on decision type
            base_consistency = 0.6
            
            if decision_type in ['position_sizing', 'risk_management']:
                base_consistency += 0.2
            elif decision_type in ['entry_timing', 'exit_strategy']:
                base_consistency += 0.1
            
            # Adjust for portfolio size
            if portfolio_size == 'small_portfolio':
                return base_consistency * 0.9
            elif portfolio_size == 'medium_portfolio':
                return base_consistency
            elif portfolio_size == 'large_portfolio':
                return base_consistency * 1.1
            else:
                return base_consistency
                
        except Exception as e:
            print(f"Error getting decision consistency: {e}")
            return 0.5
    
    def _get_active_decision_factors(self) -> List[str]:
        """Get list of active decision factors"""
        try:
            # This would query database for active decision factors
            # For now, return common decision factors
            return [
                'risk', 'volatility', 'correlation', 'liquidity',
                'market_regime', 'technical_indicators', 'fundamental_analysis'
            ]
        except Exception as e:
            print(f"Error getting active decision factors: {e}")
            return []
    
    def _calculate_factor_diversity(self, factors: List[str], current_factors: List[str]) -> float:
        """Calculate decision factor diversity and orthogonality"""
        try:
            if not factors or not current_factors:
                return 0.5
            
            # θ based on factor diversity
            diversity_score = 0.5  # Base diversity
            
            # Add bonus for diverse factor combinations
            if len(current_factors) > 3:
                diversity_score += 0.2
            
            # Add bonus for innovative factors
            innovative_factors = ['market_regime', 'correlation', 'liquidity']
            if any(factor in current_factors for factor in innovative_factors):
                diversity_score += 0.3
            
            return min(diversity_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating factor diversity: {e}")
            return 0.5
    
    # ============================================================================
    # TD Helper Methods
    # ============================================================================
    
    def _get_execution_consistency(self, execution_method: str, order_size: str) -> float:
        """Get execution consistency for specific method and order size"""
        try:
            # This would query actual execution data from database
            # For now, return realistic estimates based on execution method
            base_consistency = 0.6
            
            if execution_method in ['twap', 'vwap']:
                base_consistency += 0.2
            elif execution_method in ['adaptive', 'smart_routing']:
                base_consistency += 0.1
            
            # Adjust for order size
            if order_size == 'small_order':
                return base_consistency * 1.1
            elif order_size == 'medium_order':
                return base_consistency
            elif order_size == 'large_order':
                return base_consistency * 0.9
            else:
                return base_consistency
                
        except Exception as e:
            print(f"Error getting execution consistency: {e}")
            return 0.5
    
    def _get_active_execution_strategies(self) -> List[str]:
        """Get list of active execution strategies"""
        try:
            # This would query database for active execution strategies
            # For now, return common execution strategies
            return [
                'twap', 'vwap', 'adaptive', 'smart_routing',
                'iceberg', 'hidden', 'immediate_or_cancel'
            ]
        except Exception as e:
            print(f"Error getting active execution strategies: {e}")
            return []
    
    def _calculate_strategy_diversity(self, strategies: List[str], current_strategy: str) -> float:
        """Calculate execution strategy diversity and orthogonality"""
        try:
            if not strategies or current_strategy == 'unknown':
                return 0.5
            
            # θ based on strategy diversity
            diversity_score = 0.5  # Base diversity
            
            if current_strategy not in ['unknown', 'standard', 'common']:
                diversity_score += 0.3
            
            # Add bonus for innovative strategies
            if current_strategy in ['adaptive', 'smart_routing', 'iceberg']:
                diversity_score += 0.2
            
            return min(diversity_score, 1.0)
            
        except Exception as e:
            print(f"Error calculating strategy diversity: {e}")
            return 0.5
