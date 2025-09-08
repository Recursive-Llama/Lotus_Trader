"""
Resonance Integration for Raw Data Intelligence

Handles organic resonance integration for raw data intelligence agents. Enables agents to 
participate in φ, ρ, θ calculations that drive organic evolution through mathematical resonance.

Key Concepts:
- φ (phi): Fractal self-similarity - patterns that repeat across scales
- ρ (rho): Recursive feedback - patterns that strengthen through repetition
- θ (theta): Global resonance field - collective intelligence resonance
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from scipy.spatial.distance import cosine

from src.utils.supabase_manager import SupabaseManager


class ResonanceIntegration:
    """
    Handles organic resonance integration for raw data intelligence agents
    
    Enables agents to participate in resonance calculations that drive organic evolution:
    - φ (fractal self-similarity): Patterns that repeat across different scales
    - ρ (recursive feedback): Patterns that strengthen through repetition and feedback
    - θ (global resonance field): Collective intelligence resonance across the system
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Resonance calculation parameters
        self.phi_similarity_threshold = 0.7  # Threshold for fractal self-similarity
        self.rho_feedback_strength = 0.8  # Strength of recursive feedback
        self.theta_global_weight = 0.3  # Weight of global resonance field
        
        # Resonance enhancement parameters
        self.resonance_boost_factor = 1.5  # Factor for resonance-enhanced scoring
        self.cluster_resonance_threshold = 0.6  # Threshold for cluster resonance
        
        # Telemetry tracking
        self.telemetry_weights = {
            'sr': 0.3,  # Success rate
            'cr': 0.3,  # Consistency rate  
            'xr': 0.2,  # Cross-validation rate
            'surprise': 0.2  # Surprise factor
        }
    
    async def calculate_strand_resonance(self, strand_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate φ, ρ values that drive organic evolution
        
        Args:
            strand_data: Strand data from raw data intelligence analysis
            
        Returns:
            Dictionary with resonance values (phi, rho, theta, enhanced_score)
        """
        try:
            resonance_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'phi': 0.0,  # Fractal self-similarity
                'rho': 0.0,  # Recursive feedback
                'theta': 0.0,  # Global resonance field contribution
                'enhanced_score': 0.0,  # Resonance-enhanced score
                'telemetry': {},
                'resonance_confidence': 0.0
            }
            
            # 1. Calculate φ (fractal self-similarity)
            phi_value = await self._calculate_phi_fractal_similarity(strand_data)
            resonance_results['phi'] = phi_value
            
            # 2. Calculate ρ (recursive feedback)
            rho_value = await self._calculate_rho_recursive_feedback(strand_data)
            resonance_results['rho'] = rho_value
            
            # 3. Update telemetry (sr, cr, xr, surprise)
            telemetry = await self._update_telemetry(strand_data, phi_value, rho_value)
            resonance_results['telemetry'] = telemetry
            
            # 4. Contribute to global θ field
            theta_contribution = await self._calculate_theta_contribution(strand_data, phi_value, rho_value)
            resonance_results['theta'] = theta_contribution
            
            # 5. Calculate enhanced score
            enhanced_score = await self._calculate_enhanced_score(strand_data, phi_value, rho_value, theta_contribution)
            resonance_results['enhanced_score'] = enhanced_score
            
            # 6. Calculate resonance confidence
            resonance_confidence = await self._calculate_resonance_confidence(resonance_results)
            resonance_results['resonance_confidence'] = resonance_confidence
            
            return resonance_results
            
        except Exception as e:
            self.logger.error(f"Strand resonance calculation failed: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'phi': 0.0,
                'rho': 0.0,
                'theta': 0.0,
                'enhanced_score': 0.0,
                'telemetry': {},
                'resonance_confidence': 0.0,
                'error': str(e)
            }
    
    async def find_resonance_clusters(self, pattern_type: str) -> List[Dict[str, Any]]:
        """
        Find resonance clusters that indicate valuable patterns
        
        Args:
            pattern_type: Type of pattern to find clusters for
            
        Returns:
            List of resonance clusters with high resonance values
        """
        try:
            clusters = []
            
            # Query similar strands from database
            similar_strands = await self._query_similar_strands(pattern_type)
            
            if not similar_strands:
                return clusters
            
            # Calculate cluster resonance for each group
            for strand_group in similar_strands:
                cluster_resonance = await self._calculate_cluster_resonance(strand_group)
                
                if cluster_resonance['resonance_score'] >= self.cluster_resonance_threshold:
                    clusters.append({
                        'cluster_id': cluster_resonance['cluster_id'],
                        'resonance_score': cluster_resonance['resonance_score'],
                        'strand_count': len(strand_group),
                        'pattern_type': pattern_type,
                        'cluster_characteristics': cluster_resonance['characteristics'],
                        'organic_influence_potential': cluster_resonance['influence_potential'],
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            
            # Sort by resonance score (highest first)
            clusters.sort(key=lambda x: x['resonance_score'], reverse=True)
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Resonance cluster finding failed: {e}")
            return []
    
    async def enhance_score_with_resonance(self, strand_id: str) -> float:
        """
        Enhance strand score with resonance boost
        
        Args:
            strand_id: ID of strand to enhance
            
        Returns:
            Enhanced score with resonance boost
        """
        try:
            # Get base score from strand
            base_score = await self._get_base_score(strand_id)
            if base_score is None:
                return 0.0
            
            # Get resonance values
            resonance_data = await self._get_strand_resonance(strand_id)
            if not resonance_data:
                return base_score
            
            # Calculate resonance boost
            phi = resonance_data.get('phi', 0.0)
            rho = resonance_data.get('rho', 0.0)
            theta = resonance_data.get('theta', 0.0)
            
            # Apply enhancement formula
            resonance_boost = (phi * 0.4 + rho * 0.4 + theta * 0.2) * self.resonance_boost_factor
            enhanced_score = base_score * (1.0 + resonance_boost)
            
            # Cap enhanced score at reasonable maximum
            enhanced_score = min(enhanced_score, base_score * 3.0)
            
            return enhanced_score
            
        except Exception as e:
            self.logger.error(f"Score enhancement with resonance failed: {e}")
            return 0.0
    
    async def _calculate_phi_fractal_similarity(self, strand_data: Dict[str, Any]) -> float:
        """Calculate φ (fractal self-similarity) - patterns that repeat across scales"""
        try:
            phi_score = 0.0
            
            # Extract pattern data
            patterns = strand_data.get('patterns', [])
            if not patterns:
                return phi_score
            
            # Look for self-similar patterns across different time scales
            time_scales = ['1m', '5m', '15m', '1h', '4h', '1d']
            similarity_scores = []
            
            for i, scale1 in enumerate(time_scales):
                for scale2 in time_scales[i+1:]:
                    # Calculate similarity between patterns at different scales
                    similarity = await self._calculate_scale_similarity(strand_data, scale1, scale2)
                    similarity_scores.append(similarity)
            
            if similarity_scores:
                # φ is the average similarity across scales
                phi_score = np.mean(similarity_scores)
            
            # Look for fractal patterns in the data itself
            fractal_similarity = await self._detect_fractal_patterns(strand_data)
            phi_score = (phi_score + fractal_similarity) / 2.0
            
            return min(1.0, max(0.0, phi_score))
            
        except Exception as e:
            self.logger.error(f"φ (fractal similarity) calculation failed: {e}")
            return 0.0
    
    async def _calculate_rho_recursive_feedback(self, strand_data: Dict[str, Any]) -> float:
        """Calculate ρ (recursive feedback) - patterns that strengthen through repetition"""
        try:
            rho_score = 0.0
            
            # Look for recursive patterns in the analysis
            analysis_components = strand_data.get('analysis_components', {})
            
            # Check for feedback loops in the analysis
            feedback_strength = await self._detect_feedback_loops(analysis_components)
            rho_score += feedback_strength * 0.4
            
            # Check for pattern reinforcement
            pattern_reinforcement = await self._detect_pattern_reinforcement(strand_data)
            rho_score += pattern_reinforcement * 0.3
            
            # Check for recursive learning
            recursive_learning = await self._detect_recursive_learning(strand_data)
            rho_score += recursive_learning * 0.3
            
            return min(1.0, max(0.0, rho_score))
            
        except Exception as e:
            self.logger.error(f"ρ (recursive feedback) calculation failed: {e}")
            return 0.0
    
    async def _update_telemetry(self, strand_data: Dict[str, Any], phi: float, rho: float) -> Dict[str, float]:
        """Update telemetry (sr, cr, xr, surprise)"""
        try:
            telemetry = {
                'sr': 0.0,  # Success rate
                'cr': 0.0,  # Consistency rate
                'xr': 0.0,  # Cross-validation rate
                'surprise': 0.0  # Surprise factor
            }
            
            # Calculate success rate (sr)
            confidence = strand_data.get('confidence', 0.0)
            telemetry['sr'] = confidence
            
            # Calculate consistency rate (cr)
            patterns = strand_data.get('patterns', [])
            if len(patterns) > 1:
                pattern_consistencies = []
                for pattern in patterns:
                    pattern_consistencies.append(pattern.get('consistency', 0.0))
                telemetry['cr'] = np.mean(pattern_consistencies)
            else:
                telemetry['cr'] = confidence
            
            # Calculate cross-validation rate (xr)
            analysis_components = strand_data.get('analysis_components', {})
            if len(analysis_components) > 1:
                component_confidences = []
                for component, data in analysis_components.items():
                    if isinstance(data, dict) and 'confidence' in data:
                        component_confidences.append(data['confidence'])
                if component_confidences:
                    telemetry['xr'] = np.mean(component_confidences)
                else:
                    telemetry['xr'] = confidence
            else:
                telemetry['xr'] = confidence
            
            # Calculate surprise factor
            telemetry['surprise'] = await self._calculate_surprise_factor(strand_data, phi, rho)
            
            return telemetry
            
        except Exception as e:
            self.logger.error(f"Telemetry update failed: {e}")
            return {'sr': 0.0, 'cr': 0.0, 'xr': 0.0, 'surprise': 0.0}
    
    async def _calculate_theta_contribution(self, strand_data: Dict[str, Any], phi: float, rho: float) -> float:
        """Contribute to global θ field"""
        try:
            # θ contribution is based on how much this strand contributes to global resonance
            theta_contribution = 0.0
            
            # Base contribution from φ and ρ
            theta_contribution += (phi + rho) * 0.3
            
            # Contribution from telemetry
            telemetry = await self._update_telemetry(strand_data, phi, rho)
            telemetry_contribution = sum(telemetry.values()) / len(telemetry)
            theta_contribution += telemetry_contribution * 0.2
            
            # Contribution from pattern significance
            significant_patterns = strand_data.get('significant_patterns', [])
            if significant_patterns:
                pattern_significance = len(significant_patterns) / 10.0  # Normalize
                theta_contribution += min(0.5, pattern_significance)
            
            # Weight by global resonance field importance
            theta_contribution *= self.theta_global_weight
            
            return min(1.0, max(0.0, theta_contribution))
            
        except Exception as e:
            self.logger.error(f"θ (global resonance) contribution calculation failed: {e}")
            return 0.0
    
    async def _calculate_enhanced_score(self, strand_data: Dict[str, Any], phi: float, rho: float, theta: float) -> float:
        """Calculate enhanced score with resonance boost"""
        try:
            # Get base score
            base_score = strand_data.get('confidence', 0.0)
            
            # Calculate resonance boost
            resonance_boost = (phi * 0.4 + rho * 0.4 + theta * 0.2) * self.resonance_boost_factor
            
            # Apply enhancement
            enhanced_score = base_score * (1.0 + resonance_boost)
            
            # Cap at reasonable maximum
            enhanced_score = min(enhanced_score, base_score * 3.0)
            
            return enhanced_score
            
        except Exception as e:
            self.logger.error(f"Enhanced score calculation failed: {e}")
            return strand_data.get('confidence', 0.0)
    
    async def _calculate_resonance_confidence(self, resonance_results: Dict[str, Any]) -> float:
        """Calculate confidence in resonance calculations"""
        try:
            phi = resonance_results.get('phi', 0.0)
            rho = resonance_results.get('rho', 0.0)
            theta = resonance_results.get('theta', 0.0)
            telemetry = resonance_results.get('telemetry', {})
            
            # Base confidence from resonance values
            resonance_confidence = (phi + rho + theta) / 3.0
            
            # Boost confidence if telemetry is consistent
            if telemetry:
                telemetry_values = list(telemetry.values())
                telemetry_consistency = 1.0 - np.std(telemetry_values)
                resonance_confidence = (resonance_confidence + telemetry_consistency) / 2.0
            
            return min(1.0, max(0.0, resonance_confidence))
            
        except Exception as e:
            self.logger.error(f"Resonance confidence calculation failed: {e}")
            return 0.0
    
    async def _calculate_scale_similarity(self, strand_data: Dict[str, Any], scale1: str, scale2: str) -> float:
        """Calculate similarity between patterns at different time scales"""
        try:
            # Mock implementation - in real system, this would compare actual patterns
            # across different time scales
            
            patterns = strand_data.get('patterns', [])
            if len(patterns) < 2:
                return 0.0
            
            # Simple similarity based on pattern characteristics
            pattern_chars = []
            for pattern in patterns:
                char = {
                    'type': pattern.get('type', ''),
                    'severity': pattern.get('severity', 'low'),
                    'confidence': pattern.get('confidence', 0.0)
                }
                pattern_chars.append(char)
            
            # Calculate similarity between pattern characteristics
            similarities = []
            for i, char1 in enumerate(pattern_chars):
                for char2 in pattern_chars[i+1:]:
                    similarity = 0.0
                    if char1['type'] == char2['type']:
                        similarity += 0.5
                    if char1['severity'] == char2['severity']:
                        similarity += 0.3
                    similarity += (1.0 - abs(char1['confidence'] - char2['confidence'])) * 0.2
                    similarities.append(similarity)
            
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            self.logger.error(f"Scale similarity calculation failed: {e}")
            return 0.0
    
    async def _detect_fractal_patterns(self, strand_data: Dict[str, Any]) -> float:
        """Detect fractal patterns in the data"""
        try:
            # Mock implementation - in real system, this would use actual fractal analysis
            patterns = strand_data.get('patterns', [])
            
            if not patterns:
                return 0.0
            
            # Simple fractal detection based on pattern repetition
            pattern_types = [p.get('type', '') for p in patterns]
            unique_types = len(set(pattern_types))
            total_patterns = len(pattern_types)
            
            # Higher fractal score if patterns repeat (self-similarity)
            if total_patterns > 0:
                fractal_score = (total_patterns - unique_types) / total_patterns
                return min(1.0, fractal_score)
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Fractal pattern detection failed: {e}")
            return 0.0
    
    async def _detect_feedback_loops(self, analysis_components: Dict[str, Any]) -> float:
        """Detect feedback loops in analysis components"""
        try:
            if len(analysis_components) < 2:
                return 0.0
            
            # Look for circular dependencies in analysis components
            feedback_strength = 0.0
            
            component_names = list(analysis_components.keys())
            for i, comp1 in enumerate(component_names):
                for comp2 in component_names[i+1:]:
                    # Check if components reference each other
                    comp1_data = analysis_components[comp1]
                    comp2_data = analysis_components[comp2]
                    
                    if isinstance(comp1_data, dict) and isinstance(comp2_data, dict):
                        # Simple feedback detection based on shared patterns
                        comp1_patterns = comp1_data.get('patterns', [])
                        comp2_patterns = comp2_data.get('patterns', [])
                        
                        if comp1_patterns and comp2_patterns:
                            shared_patterns = set([p.get('type', '') for p in comp1_patterns]) & \
                                           set([p.get('type', '') for p in comp2_patterns])
                            if shared_patterns:
                                feedback_strength += len(shared_patterns) / max(len(comp1_patterns), len(comp2_patterns))
            
            return min(1.0, feedback_strength / len(component_names))
            
        except Exception as e:
            self.logger.error(f"Feedback loop detection failed: {e}")
            return 0.0
    
    async def _detect_pattern_reinforcement(self, strand_data: Dict[str, Any]) -> float:
        """Detect pattern reinforcement"""
        try:
            patterns = strand_data.get('patterns', [])
            if len(patterns) < 2:
                return 0.0
            
            # Look for patterns that reinforce each other
            reinforcement_score = 0.0
            
            for i, pattern1 in enumerate(patterns):
                for pattern2 in patterns[i+1:]:
                    # Check if patterns are mutually reinforcing
                    if self._are_patterns_reinforcing(pattern1, pattern2):
                        reinforcement_score += 0.1
            
            return min(1.0, reinforcement_score)
            
        except Exception as e:
            self.logger.error(f"Pattern reinforcement detection failed: {e}")
            return 0.0
    
    async def _detect_recursive_learning(self, strand_data: Dict[str, Any]) -> float:
        """Detect recursive learning patterns"""
        try:
            # Look for evidence of recursive learning in the analysis
            analysis_components = strand_data.get('analysis_components', {})
            
            recursive_score = 0.0
            
            # Check if analysis components show learning progression
            for component, data in analysis_components.items():
                if isinstance(data, dict):
                    # Look for learning indicators
                    if 'learning_progression' in data:
                        recursive_score += 0.3
                    if 'recursive_improvement' in data:
                        recursive_score += 0.3
                    if 'feedback_integration' in data:
                        recursive_score += 0.4
            
            return min(1.0, recursive_score)
            
        except Exception as e:
            self.logger.error(f"Recursive learning detection failed: {e}")
            return 0.0
    
    async def _calculate_surprise_factor(self, strand_data: Dict[str, Any], phi: float, rho: float) -> float:
        """Calculate surprise factor"""
        try:
            # Surprise factor is based on unexpected patterns or high resonance
            surprise = 0.0
            
            # High φ or ρ values are surprising
            surprise += min(0.5, phi * 0.5)
            surprise += min(0.5, rho * 0.5)
            
            # Novel patterns are surprising
            patterns = strand_data.get('patterns', [])
            for pattern in patterns:
                if pattern.get('novelty_score', 0) > 0.7:
                    surprise += 0.2
            
            # Unexpected confidence levels are surprising
            confidence = strand_data.get('confidence', 0.0)
            if confidence > 0.9 or confidence < 0.1:
                surprise += 0.3
            
            return min(1.0, surprise)
            
        except Exception as e:
            self.logger.error(f"Surprise factor calculation failed: {e}")
            return 0.0
    
    def _are_patterns_reinforcing(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
        """Check if two patterns are mutually reinforcing"""
        try:
            # Simple reinforcement check
            type1 = pattern1.get('type', '')
            type2 = pattern2.get('type', '')
            
            # Patterns are reinforcing if they're similar types
            if type1 == type2:
                return True
            
            # Patterns are reinforcing if they have complementary characteristics
            severity1 = pattern1.get('severity', 'low')
            severity2 = pattern2.get('severity', 'low')
            
            if severity1 == severity2 and severity1 in ['high', 'medium']:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Pattern reinforcement check failed: {e}")
            return False
    
    async def _query_similar_strands(self, pattern_type: str) -> List[List[Dict[str, Any]]]:
        """Query similar strands from database"""
        try:
            # Mock implementation - in real system, this would query the database
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Similar strands query failed: {e}")
            return []
    
    async def _calculate_cluster_resonance(self, strand_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate resonance for a group of strands"""
        try:
            if not strand_group:
                return {'resonance_score': 0.0, 'cluster_id': '', 'characteristics': {}, 'influence_potential': 0.0}
            
            # Calculate average resonance across the group
            resonance_scores = []
            for strand in strand_group:
                resonance = await self.calculate_strand_resonance(strand)
                resonance_scores.append(resonance.get('enhanced_score', 0.0))
            
            cluster_resonance = np.mean(resonance_scores)
            
            return {
                'resonance_score': cluster_resonance,
                'cluster_id': f"cluster_{hash(str(strand_group)) % 10000}",
                'characteristics': {
                    'strand_count': len(strand_group),
                    'avg_resonance': cluster_resonance,
                    'resonance_variance': np.var(resonance_scores)
                },
                'influence_potential': cluster_resonance * len(strand_group)
            }
            
        except Exception as e:
            self.logger.error(f"Cluster resonance calculation failed: {e}")
            return {'resonance_score': 0.0, 'cluster_id': '', 'characteristics': {}, 'influence_potential': 0.0}
    
    async def _get_base_score(self, strand_id: str) -> Optional[float]:
        """Get base score from strand"""
        try:
            # Mock implementation - in real system, this would query the database
            return 0.5  # Default base score
            
        except Exception as e:
            self.logger.error(f"Base score retrieval failed: {e}")
            return None
    
    async def _get_strand_resonance(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Get resonance data for a strand"""
        try:
            # Mock implementation - in real system, this would query the database
            return {
                'phi': 0.5,
                'rho': 0.5,
                'theta': 0.5
            }
            
        except Exception as e:
            self.logger.error(f"Strand resonance retrieval failed: {e}")
            return None
