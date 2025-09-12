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
        
        # Orthogonality threshold for ensemble diversity
        self.orthogonality_threshold = 0.3
        
        # Meta-learning threshold for acceleration
        self.meta_learning_threshold = 0.7
    
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
            # Simple pattern strength calculation
            confidence = pattern_data.get('confidence', 0.0)
            quality = pattern_data.get('quality', 0.0)
            return confidence * quality
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
    
    def _calculate_correlation(self, pattern1: Dict[str, Any], 
                              pattern2: Dict[str, Any]) -> float:
        """Calculate correlation between two patterns"""
        try:
            # Simple correlation calculation
            values1 = pattern1.get('values', [])
            values2 = pattern2.get('values', [])
            
            if len(values1) != len(values2) or len(values1) == 0:
                return 0.0
            
            correlation = np.corrcoef(values1, values2)[0, 1]
            return abs(correlation) if not np.isnan(correlation) else 0.0
        except:
            return 0.0
