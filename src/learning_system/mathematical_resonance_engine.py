"""
Mathematical Resonance Engine

Implements Simons' resonance equations (φ, ρ, θ, ω) and selection mechanisms
for the centralized learning system. This is the mathematical consciousness
that drives pattern selection, learning evolution, and ensemble diversity.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ResonanceState:
    """Current state of resonance variables"""
    phi: float  # Fractal self-similarity
    rho: float  # Recursive feedback strength
    theta: float  # Global field strength
    omega: float  # Resonance acceleration
    timestamp: datetime


@dataclass
class SelectionScore:
    """Simons' selection score components"""
    accuracy: float
    precision: float
    stability: float
    orthogonality: float
    cost: float
    total_score: float


class MathematicalResonanceEngine:
    """
    Mathematical Resonance Engine implementing Simons' principles
    
    This is the mathematical consciousness that drives:
    - Pattern quality assessment (φ)
    - Learning system evolution (ρ)
    - Collective intelligence (θ)
    - Meta-learning acceleration (ω)
    - Pattern selection (S_i)
    - Ensemble diversity maintenance
    """
    
    def __init__(self, planck_constant: float = 0.1):
        """
        Initialize the resonance engine
        
        Args:
            planck_constant: Scaling factor for resonance calculations
        """
        self.planck_constant = planck_constant
        self.resonance_state = ResonanceState(1.0, 0.0, 0.0, 0.0, datetime.now(timezone.utc))
        
        # Selection score weights (Simons-aligned)
        self.selection_weights = {
            'accuracy': 0.30,
            'precision': 0.25,
            'stability': 0.25,
            'orthogonality': 0.15,
            'cost': 0.05
        }
        
        # Learning system already has cluster size limits and quality thresholds
        
        # Meta-learning threshold for acceleration
        self.meta_learning_threshold = 0.7
        
        # Module-specific configuration
        self.module_configs = {
            'rdi': {
                'name': 'Raw Data Intelligence',
                'strand_kind': 'pattern',
                'phi_focus': 'cross_timeframe_consistency',
                'rho_focus': 'pattern_success_rate',
                'theta_focus': 'pattern_diversity',
                'omega_focus': 'detection_improvement'
            },
            'cil': {
                'name': 'Central Intelligence Layer',
                'strand_kind': 'prediction_review',
                'phi_focus': 'prediction_consistency',
                'rho_focus': 'prediction_accuracy',
                'theta_focus': 'method_diversity',
                'omega_focus': 'prediction_improvement'
            },
            'ctp': {
                'name': 'Conditional Trading Planner',
                'strand_kind': 'conditional_trading_plan',
                'phi_focus': 'plan_consistency',
                'rho_focus': 'plan_profitability',
                'theta_focus': 'strategy_diversity',
                'omega_focus': 'plan_improvement'
            },
            'dm': {
                'name': 'Decision Maker',
                'strand_kind': 'trading_decision',
                'phi_focus': 'decision_consistency',
                'rho_focus': 'decision_outcome_quality',
                'theta_focus': 'factor_diversity',
                'omega_focus': 'decision_improvement'
            },
            'td': {
                'name': 'Trader',
                'strand_kind': 'execution_outcome',
                'phi_focus': 'execution_consistency',
                'rho_focus': 'execution_success',
                'theta_focus': 'strategy_diversity',
                'omega_focus': 'execution_improvement'
            }
        }
    
    def calculate_phi(self, pattern_data: Dict[str, Any], timeframes: List[str]) -> float:
        """
        Calculate φ (Fractal Self-Similarity)
        
        Formula: φ_i = φ_(i-1) × ρ_i
        
        Args:
            pattern_data: Pattern data across timeframes
            timeframes: List of timeframes to check consistency
            
        Returns:
            φ value representing fractal consistency
        """
        try:
            phi_values = []
            
            for timeframe in timeframes:
                if timeframe in pattern_data:
                    # Calculate pattern strength for this timeframe
                    pattern_strength = self._calculate_pattern_strength(
                        pattern_data[timeframe]
                    )
                    phi_values.append(pattern_strength)
            
            if not phi_values:
                return 0.0
            
            # φ = product of pattern strengths across timeframes
            phi = np.prod(phi_values)
            
            # Update resonance state
            self.resonance_state.phi = phi
            
            return phi
            
        except Exception as e:
            print(f"Error calculating φ: {e}")
            return 0.0
    
    def calculate_rho(self, learning_outcome: Dict[str, Any]) -> float:
        """
        Calculate ρ (Recursive Feedback)
        
        Formula: ρ_i(t+1) = ρ_i(t) + α × ∆φ(t)
        
        Args:
            learning_outcome: Outcome of learning process
            
        Returns:
            ρ value representing learning strength
        """
        try:
            # Calculate surprise (how unexpected the outcome was)
            surprise = self._calculate_surprise(learning_outcome)
            
            # Calculate φ change
            delta_phi = learning_outcome.get('phi_change', 0.0)
            
            # Learning rate = α × surprise
            alpha = 0.1  # Learning rate parameter
            learning_rate = alpha * surprise
            
            # ρ = previous ρ + learning rate × φ change
            new_rho = self.resonance_state.rho + learning_rate * delta_phi
            
            # Update resonance state
            self.resonance_state.rho = new_rho
            
            return new_rho
            
        except Exception as e:
            print(f"Error calculating ρ: {e}")
            return self.resonance_state.rho
    
    def calculate_theta(self, all_braids: List[Dict[str, Any]]) -> float:
        """
        Calculate θ (Global Field)
        
        Formula: θ_i = θ_(i-1) + ℏ × ∑(φ_j × ρ_j)
        
        Args:
            all_braids: List of all successful braids
            
        Returns:
            θ value representing global intelligence field
        """
        try:
            theta_contribution = 0.0
            
            for braid in all_braids:
                phi = braid.get('phi', 0.0)
                rho = braid.get('rho', 0.0)
                
                # Contribution = ℏ × (φ × ρ)
                contribution = self.planck_constant * (phi * rho)
                theta_contribution += contribution
            
            # θ = previous θ + total contribution
            new_theta = self.resonance_state.theta + theta_contribution
            
            # Update resonance state
            self.resonance_state.theta = new_theta
            
            return new_theta
            
        except Exception as e:
            print(f"Error calculating θ: {e}")
            return self.resonance_state.theta
    
    def calculate_omega(self, global_theta: float, learning_strength: float) -> float:
        """
        Calculate ω (Resonance Acceleration)
        
        Formula: ωᵢ(t+1) = ωᵢ(t) + ℏ × ψ(ωᵢ) × ∫(⟡, θᵢ, ρᵢ)
        
        Args:
            global_theta: Current global field strength
            learning_strength: Current learning strength (ρ)
            
        Returns:
            ω value representing resonance acceleration
        """
        try:
            # ψ function (resonance function)
            psi_omega = self._psi_function(self.resonance_state.omega)
            
            # ∫ function (integral of resonance components)
            integral_value = self._integral_function(global_theta, learning_strength)
            
            # Acceleration = ℏ × ψ(ω) × ∫(θ, ρ)
            acceleration = self.planck_constant * psi_omega * integral_value
            
            # ω = previous ω + acceleration
            new_omega = self.resonance_state.omega + acceleration
            
            # Update resonance state
            self.resonance_state.omega = new_omega
            
            return new_omega
            
        except Exception as e:
            print(f"Error calculating ω: {e}")
            return self.resonance_state.omega
    
    def calculate_selection_score(self, pattern_data: Dict[str, Any]) -> SelectionScore:
        """
        Calculate S_i (Selection Score) - Simons' fitness function
        
        Formula: S_i = w_accuracy * sq_accuracy + w_precision * sq_precision + 
                 w_stability * sq_stability + w_orthogonality * sq_orthogonality - 
                 w_cost * sq_cost
        
        Args:
            pattern_data: Pattern data to score
            
        Returns:
            SelectionScore with all components
        """
        try:
            # Calculate individual components
            accuracy = self._calculate_accuracy(pattern_data)
            precision = self._calculate_precision(pattern_data)
            stability = self._calculate_stability(pattern_data)
            orthogonality = self._calculate_orthogonality(pattern_data)
            cost = self._calculate_cost(pattern_data)
            
            # Calculate weighted total score
            total_score = (
                self.selection_weights['accuracy'] * accuracy +
                self.selection_weights['precision'] * precision +
                self.selection_weights['stability'] * stability +
                self.selection_weights['orthogonality'] * orthogonality -
                self.selection_weights['cost'] * cost
            )
            
            return SelectionScore(
                accuracy=accuracy,
                precision=precision,
                stability=stability,
                orthogonality=orthogonality,
                cost=cost,
                total_score=total_score
            )
            
        except Exception as e:
            print(f"Error calculating selection score: {e}")
            return SelectionScore(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def calculate_pattern_weight(self, pattern: Dict[str, Any], 
                                age_days: float = 0.0) -> float:
        """
        Calculate natural weight for a pattern based on success and age
        
        Args:
            pattern: Pattern data
            age_days: Age of pattern in days
            
        Returns:
            Weight for the pattern (higher = more important)
        """
        try:
            # Base weight
            weight = 1.0
            
            # Success weighting
            if pattern.get('success', False):
                weight *= self.success_weight
            
            # Time decay
            if age_days > 0:
                weight *= (self.time_decay_factor ** age_days)
            
            # Confidence weighting
            confidence = pattern.get('confidence', 0.5)
            weight *= confidence
            
            return weight
            
        except Exception as e:
            print(f"Error calculating pattern weight: {e}")
            return 1.0
    
    def should_evolve_learning_methods(self) -> bool:
        """
        Check if learning methods should evolve based on ω
        
        Returns:
            True if methods should evolve, False otherwise
        """
        return self.resonance_state.omega > self.meta_learning_threshold
    
    def get_resonance_state(self) -> ResonanceState:
        """
        Get current resonance state
        
        Returns:
            Current ResonanceState
        """
        return self.resonance_state
    
    def _calculate_pattern_strength(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate pattern strength for a single timeframe"""
        try:
            # For RDI patterns, look in module_intelligence
            if 'module_intelligence' in pattern_data:
                confidence = pattern_data.get('module_intelligence', {}).get('confidence', 0.0)
                return confidence
            
            # For other patterns, look in content or metadata
            confidence = pattern_data.get('confidence', 0.0)
            strength = pattern_data.get('strength', confidence)
            quality = pattern_data.get('quality', confidence)
            
            # Return the best available metric
            return max(confidence, strength, quality)
        except:
            return 0.0
    
    def _calculate_surprise(self, learning_outcome: Dict[str, Any]) -> float:
        """Calculate surprise value for learning outcome"""
        try:
            expected = learning_outcome.get('expected', 0.5)
            actual = learning_outcome.get('actual', 0.5)
            return abs(actual - expected)
        except:
            return 0.0
    
    def _psi_function(self, omega: float) -> float:
        """ψ function for resonance calculation"""
        try:
            # Sigmoid function for resonance
            return 1.0 / (1.0 + np.exp(-omega))
        except:
            return 0.0
    
    def _integral_function(self, theta: float, rho: float) -> float:
        """∫ function for resonance calculation"""
        try:
            # Simple integral approximation
            return theta * rho
        except:
            return 0.0
    
    def _calculate_accuracy(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate accuracy component of selection score"""
        try:
            # Directional hit rate, confidence-weighted
            hits = pattern_data.get('hits', 0)
            total = pattern_data.get('total', 1)
            confidence = pattern_data.get('confidence', 0.0)
            
            accuracy = hits / total if total > 0 else 0.0
            return accuracy * confidence
        except:
            return 0.0
    
    def _calculate_precision(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate precision component of selection score"""
        try:
            # Statistical significance
            t_stat = pattern_data.get('t_stat', 0.0)
            return 1.0 / (1.0 + np.exp(-t_stat))  # Logistic function
        except:
            return 0.0
    
    def _calculate_stability(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate stability component of selection score"""
        try:
            # IR stability over time
            rolling_ir = pattern_data.get('rolling_ir', [])
            if not rolling_ir:
                return 0.0
            
            mean_ir = np.mean(rolling_ir)
            std_ir = np.std(rolling_ir)
            
            if abs(mean_ir) < 1e-6:
                return 0.0
            
            stability = 1.0 - (std_ir / abs(mean_ir))
            return max(0.0, min(1.0, stability))
        except:
            return 0.0
    
    def _calculate_orthogonality(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate orthogonality component of selection score"""
        try:
            # Correlation with other patterns
            correlations = pattern_data.get('correlations', [])
            if not correlations:
                return 1.0
            
            max_correlation = max(correlations)
            return 1.0 - max_correlation
        except:
            return 1.0
    
    def _calculate_cost(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate cost component of selection score"""
        try:
            # Processing and storage cost
            processing_cost = pattern_data.get('processing_cost', 0.0)
            storage_cost = pattern_data.get('storage_cost', 0.0)
            return processing_cost + storage_cost
        except:
            return 0.0
    
    # ============================================================================
    # MODULE-SPECIFIC RESONANCE CALCULATIONS
    # ============================================================================
    
    def calculate_module_resonance(self, strand: Dict[str, Any], module_type: str) -> Dict[str, float]:
        """
        Calculate module-specific resonance scores (φ, ρ, θ, ω)
        
        Args:
            strand: Strand data from database
            module_type: Module type ('rdi', 'cil', 'ctp', 'dm', 'td')
            
        Returns:
            Dictionary with module-specific resonance scores
        """
        try:
            if module_type not in self.module_configs:
                raise ValueError(f"Unknown module type: {module_type}")
            
            config = self.module_configs[module_type]
            
            # Calculate module-specific φ, ρ, θ, ω
            phi = self._calculate_module_phi(strand, module_type)
            rho = self._calculate_module_rho(strand, module_type)
            theta = self._calculate_module_theta(strand, module_type)
            omega = self._calculate_module_omega(strand, module_type)
            
            return {
                'phi': phi,
                'rho': rho,
                'theta': theta,
                'omega': omega,
                'module_type': module_type,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Error calculating module resonance for {module_type}: {e}")
            return {
                'phi': 0.0,
                'rho': 0.0,
                'theta': 0.0,
                'omega': 0.0,
                'module_type': module_type,
                'error': str(e)
            }
    
    def _calculate_module_phi(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate φ (Fractal Self-Similarity) for specific module"""
        try:
            if module_type == 'rdi':
                # RDI: Cross-timeframe pattern consistency
                pattern_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
                confidence = strand.get('module_intelligence', {}).get('confidence', 0.0)
                
                # Simple fractal consistency based on confidence
                return min(confidence * 1.2, 1.0)
                
            elif module_type == 'cil':
                # CIL: Prediction consistency across timeframes
                success = strand.get('content', {}).get('success', False)
                confidence = strand.get('content', {}).get('confidence', 0.0)
                
                # Consistency = success rate * confidence
                return (1.0 if success else 0.0) * confidence
                
            elif module_type == 'ctp':
                # CTP: Plan consistency across market conditions
                profitability = strand.get('content', {}).get('profitability', 0.0)
                risk_adjusted = strand.get('content', {}).get('risk_adjusted_return', 0.0)
                
                # Consistency = profitability * risk adjustment
                return min(profitability * risk_adjusted, 1.0)
                
            elif module_type == 'dm':
                # DM: Decision consistency across portfolio sizes
                outcome_quality = strand.get('content', {}).get('outcome_quality', 0.0)
                risk_management = strand.get('content', {}).get('risk_management_effectiveness', 0.0)
                
                # Consistency = outcome quality * risk management
                return min(outcome_quality * risk_management, 1.0)
                
            elif module_type == 'td':
                # TD: Execution consistency across order sizes
                execution_success = strand.get('content', {}).get('execution_success', 0.0)
                slippage_min = strand.get('content', {}).get('slippage_minimization', 0.0)
                
                # Consistency = success rate * slippage minimization
                return min(execution_success * slippage_min, 1.0)
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating φ for {module_type}: {e}")
            return 0.0
    
    def _calculate_module_rho(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate ρ (Recursive Feedback) for specific module"""
        try:
            if module_type == 'rdi':
                # RDI: Pattern success rate based on outcomes
                success_rate = strand.get('module_intelligence', {}).get('success_rate', 0.0)
                confidence = strand.get('sig_confidence', 0.0)
                
                # ρ = success rate * confidence
                return success_rate * confidence
                
            elif module_type == 'cil':
                # CIL: Prediction accuracy based on outcomes
                success = strand.get('content', {}).get('success', False)
                return_pct = strand.get('content', {}).get('return_pct', 0.0)
                
                # ρ = success + return percentage
                if success:
                    return min(1.0 + (return_pct * 0.1), 2.0)
                else:
                    return 0.5
                
            elif module_type == 'ctp':
                # CTP: Plan profitability based on outcomes
                profitability = strand.get('content', {}).get('profitability', 0.0)
                risk_adjusted = strand.get('content', {}).get('risk_adjusted_return', 0.0)
                
                # ρ = profitability * risk adjustment
                return profitability * risk_adjusted
                
            elif module_type == 'dm':
                # DM: Decision outcome quality
                outcome_quality = strand.get('content', {}).get('outcome_quality', 0.0)
                risk_management = strand.get('content', {}).get('risk_management_effectiveness', 0.0)
                
                # ρ = outcome quality * risk management
                return outcome_quality * risk_management
                
            elif module_type == 'td':
                # TD: Execution success based on outcomes
                execution_success = strand.get('content', {}).get('execution_success', 0.0)
                slippage_min = strand.get('content', {}).get('slippage_minimization', 0.0)
                
                # ρ = execution success * slippage minimization
                return execution_success * slippage_min
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating ρ for {module_type}: {e}")
            return 0.0
    
    def _calculate_module_theta(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate θ (Global Field) for specific module"""
        try:
            if module_type == 'rdi':
                # RDI: Pattern type diversity
                pattern_type = strand.get('module_intelligence', {}).get('pattern_type', 'unknown')
                motif_family = strand.get('motif_family', 'unknown')
                
                # θ = diversity of pattern types and families
                diversity_score = 0.5  # Base diversity
                if pattern_type != 'unknown':
                    diversity_score += 0.3
                if motif_family != 'unknown':
                    diversity_score += 0.2
                
                return min(diversity_score, 1.0)
                
            elif module_type == 'cil':
                # CIL: Prediction method diversity
                method = strand.get('content', {}).get('method', 'unknown')
                meta_type = strand.get('strategic_meta_type', 'unknown')
                
                # θ = diversity of prediction methods
                diversity_score = 0.5  # Base diversity
                if method != 'unknown':
                    diversity_score += 0.3
                if meta_type != 'unknown':
                    diversity_score += 0.2
                
                return min(diversity_score, 1.0)
                
            elif module_type == 'ctp':
                # CTP: Plan type diversity
                plan_type = strand.get('content', {}).get('plan_type', 'unknown')
                strategy = strand.get('content', {}).get('strategy', 'unknown')
                
                # θ = diversity of plan types and strategies
                diversity_score = 0.5  # Base diversity
                if plan_type != 'unknown':
                    diversity_score += 0.3
                if strategy != 'unknown':
                    diversity_score += 0.2
                
                return min(diversity_score, 1.0)
                
            elif module_type == 'dm':
                # DM: Decision factor diversity
                decision_type = strand.get('content', {}).get('decision_type', 'unknown')
                factors = strand.get('content', {}).get('decision_factors', [])
                
                # θ = diversity of decision factors
                diversity_score = 0.5  # Base diversity
                if decision_type != 'unknown':
                    diversity_score += 0.3
                if factors and len(factors) > 1:
                    diversity_score += 0.2
                
                return min(diversity_score, 1.0)
                
            elif module_type == 'td':
                # TD: Execution strategy diversity
                execution_method = strand.get('content', {}).get('execution_method', 'unknown')
                strategy = strand.get('content', {}).get('execution_strategy', 'unknown')
                
                # θ = diversity of execution strategies
                diversity_score = 0.5  # Base diversity
                if execution_method != 'unknown':
                    diversity_score += 0.3
                if strategy != 'unknown':
                    diversity_score += 0.2
                
                return min(diversity_score, 1.0)
            
            return 0.0
            
        except Exception as e:
            print(f"Error calculating θ for {module_type}: {e}")
            return 0.0
    
    def _calculate_module_omega(self, strand: Dict[str, Any], module_type: str) -> float:
        """Calculate ω (Meta-Evolution) for specific module"""
        try:
            # Get historical performance for this module type
            historical_quality = self._get_historical_module_quality(strand, module_type)
            current_quality = self._get_current_module_quality(strand, module_type)
            
            # Calculate improvement rate
            if historical_quality > 0:
                improvement_rate = (current_quality - historical_quality) / historical_quality
            else:
                improvement_rate = 0.0
            
            # ω based on learning improvement (0.5 to 2.0 range)
            if improvement_rate > 0:
                return min(1.0 + improvement_rate, 2.0)
            else:
                return max(0.5 + (improvement_rate * 0.5), 0.0)
            
        except Exception as e:
            print(f"Error calculating ω for {module_type}: {e}")
            return 1.0
    
    def _get_historical_module_quality(self, strand: Dict[str, Any], module_type: str) -> float:
        """Get historical quality for module-specific improvement calculation"""
        try:
            # This would query the database for historical performance
            # For now, return a default value
            return 0.5
        except:
            return 0.5
    
    def _get_current_module_quality(self, strand: Dict[str, Any], module_type: str) -> float:
        """Get current quality for module-specific improvement calculation"""
        try:
            if module_type == 'rdi':
                return strand.get('sig_confidence', 0.0)
            elif module_type == 'cil':
                return strand.get('content', {}).get('confidence', 0.0)
            elif module_type == 'ctp':
                return strand.get('content', {}).get('profitability', 0.0)
            elif module_type == 'dm':
                return strand.get('content', {}).get('outcome_quality', 0.0)
            elif module_type == 'td':
                return strand.get('content', {}).get('execution_success', 0.0)
            return 0.0
        except:
            return 0.0
    
