"""
Execution Resonance Integration

Handles organic resonance integration for trader agents, enabling them to participate
in φ, ρ, θ calculations that drive organic evolution across the system.

Key Features:
- φ (Execution Pattern Self-Similarity): Consistency across execution scales/components
- ρ (Execution Feedback Loops): Consistency over time/observations  
- θ (Global Execution Resonance Field): System-wide execution resonance
- Execution resonance clusters for pattern discovery
- Execution score enhancement with resonance boost
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResonanceMetrics:
    """Execution resonance metrics for organic evolution"""
    phi: float  # Execution pattern self-similarity
    rho: float  # Execution feedback loops
    theta: float  # Global execution resonance field
    execution_sr: float  # Execution success rate
    execution_cr: float  # Execution consistency rate
    execution_xr: float  # Execution cross-correlation rate
    execution_surprise: float  # Execution surprise factor
    timestamp: datetime


class ExecutionResonanceIntegration:
    """Handles organic resonance integration for trader agents"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.resonance_cache = {}
        self.execution_patterns = {}
        
    async def calculate_execution_resonance(self, execution_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate φ, ρ values for execution patterns that drive organic evolution
        
        Args:
            execution_data: Execution data including results, metrics, and context
            
        Returns:
            Dict containing φ, ρ, θ values and execution telemetry
        """
        try:
            # Extract execution pattern data
            execution_pattern = self._extract_execution_pattern(execution_data)
            
            # Calculate φ (execution pattern self-similarity)
            phi = await self._calculate_execution_phi(execution_pattern)
            
            # Calculate ρ (execution feedback loops)
            rho = await self._calculate_execution_rho(execution_pattern)
            
            # Update execution telemetry
            telemetry = await self._update_execution_telemetry(execution_data, phi, rho)
            
            # Contribute to global execution θ field
            theta = await self._contribute_to_global_execution_theta(phi, rho)
            
            resonance_metrics = ExecutionResonanceMetrics(
                phi=phi,
                rho=rho,
                theta=theta,
                execution_sr=telemetry['execution_sr'],
                execution_cr=telemetry['execution_cr'],
                execution_xr=telemetry['execution_xr'],
                execution_surprise=telemetry['execution_surprise'],
                timestamp=datetime.now()
            )
            
            # Cache resonance metrics
            self._cache_resonance_metrics(execution_data.get('execution_id'), resonance_metrics)
            
            logger.info(f"Calculated execution resonance: φ={phi:.3f}, ρ={rho:.3f}, θ={theta:.3f}")
            
            return {
                'phi': phi,
                'rho': rho,
                'theta': theta,
                'execution_sr': telemetry['execution_sr'],
                'execution_cr': telemetry['execution_cr'],
                'execution_xr': telemetry['execution_xr'],
                'execution_surprise': telemetry['execution_surprise'],
                'timestamp': resonance_metrics.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating execution resonance: {e}")
            return self._get_default_resonance_metrics()
    
    async def find_execution_resonance_clusters(self, execution_type: str) -> List[Dict[str, Any]]:
        """
        Find execution resonance clusters that indicate valuable execution patterns
        
        Args:
            execution_type: Type of execution to find clusters for
            
        Returns:
            List of execution cluster information for organic influence
        """
        try:
            # Query similar execution strands from AD_strands table
            similar_strands = await self._query_similar_execution_strands(execution_type)
            
            if not similar_strands:
                logger.warning(f"No similar execution strands found for type: {execution_type}")
                return []
            
            # Calculate execution cluster resonance
            clusters = await self._calculate_execution_cluster_resonance(similar_strands)
            
            # Identify high-resonance execution patterns
            high_resonance_clusters = [
                cluster for cluster in clusters 
                if cluster['resonance_score'] > 0.7
            ]
            
            logger.info(f"Found {len(high_resonance_clusters)} high-resonance execution clusters")
            
            return high_resonance_clusters
            
        except Exception as e:
            logger.error(f"Error finding execution resonance clusters: {e}")
            return []
    
    async def enhance_execution_score_with_resonance(self, execution_strand_id: str) -> float:
        """
        Enhance execution score with resonance boost
        
        Args:
            execution_strand_id: ID of the execution strand to enhance
            
        Returns:
            Enhanced execution score with resonance boost
        """
        try:
            # Get base execution score
            base_score = await self._get_base_execution_score(execution_strand_id)
            
            # Get resonance metrics for this strand
            resonance_metrics = await self._get_strand_resonance_metrics(execution_strand_id)
            
            if not resonance_metrics:
                logger.warning(f"No resonance metrics found for strand: {execution_strand_id}")
                return base_score
            
            # Calculate execution resonance boost
            resonance_boost = self._calculate_execution_resonance_boost(resonance_metrics)
            
            # Apply execution enhancement formula
            enhanced_score = base_score * (1 + resonance_boost * 0.2)  # 20% max boost
            
            logger.info(f"Enhanced execution score: {base_score:.3f} -> {enhanced_score:.3f} (boost: {resonance_boost:.3f})")
            
            return enhanced_score
            
        except Exception as e:
            logger.error(f"Error enhancing execution score: {e}")
            return 0.0
    
    def _extract_execution_pattern(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract execution pattern data for resonance calculation"""
        return {
            'execution_type': execution_data.get('execution_type', 'unknown'),
            'venue': execution_data.get('venue', 'unknown'),
            'symbol': execution_data.get('symbol', 'unknown'),
            'execution_quality': execution_data.get('execution_quality', 0.0),
            'slippage': execution_data.get('slippage', 0.0),
            'fill_time': execution_data.get('fill_time', 0.0),
            'volume': execution_data.get('volume', 0.0),
            'price_impact': execution_data.get('price_impact', 0.0),
            'market_conditions': execution_data.get('market_conditions', {}),
            'execution_strategy': execution_data.get('execution_strategy', 'unknown')
        }
    
    async def _calculate_execution_phi(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate φ (execution pattern self-similarity)"""
        try:
            # Get historical execution patterns for comparison
            historical_patterns = await self._get_historical_execution_patterns(execution_pattern)
            
            if not historical_patterns:
                return 0.5  # Default moderate similarity
            
            # Calculate similarity scores
            similarities = []
            for hist_pattern in historical_patterns:
                similarity = self._calculate_pattern_similarity(execution_pattern, hist_pattern)
                similarities.append(similarity)
            
            # φ is the average similarity (self-similarity across scales)
            phi = np.mean(similarities) if similarities else 0.5
            
            return max(0.0, min(1.0, phi))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating execution φ: {e}")
            return 0.5
    
    async def _calculate_execution_rho(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate ρ (execution feedback loops)"""
        try:
            # Get recent execution patterns for feedback analysis
            recent_patterns = await self._get_recent_execution_patterns(execution_pattern, hours=24)
            
            if len(recent_patterns) < 2:
                return 0.5  # Default moderate feedback
            
            # Calculate consistency over time (feedback loop strength)
            consistency_scores = []
            for i in range(1, len(recent_patterns)):
                consistency = self._calculate_pattern_consistency(
                    recent_patterns[i-1], recent_patterns[i]
                )
                consistency_scores.append(consistency)
            
            # ρ is the average consistency (feedback loop strength)
            rho = np.mean(consistency_scores) if consistency_scores else 0.5
            
            return max(0.0, min(1.0, rho))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating execution ρ: {e}")
            return 0.5
    
    async def _update_execution_telemetry(self, execution_data: Dict[str, Any], phi: float, rho: float) -> Dict[str, float]:
        """Update execution telemetry with resonance values"""
        try:
            # Calculate execution success rate
            execution_sr = await self._calculate_execution_success_rate(execution_data)
            
            # Calculate execution consistency rate
            execution_cr = await self._calculate_execution_consistency_rate(execution_data)
            
            # Calculate execution cross-correlation rate
            execution_xr = await self._calculate_execution_cross_correlation_rate(execution_data)
            
            # Calculate execution surprise factor
            execution_surprise = self._calculate_execution_surprise(execution_data, phi, rho)
            
            return {
                'execution_sr': execution_sr,
                'execution_cr': execution_cr,
                'execution_xr': execution_xr,
                'execution_surprise': execution_surprise
            }
            
        except Exception as e:
            logger.error(f"Error updating execution telemetry: {e}")
            return {
                'execution_sr': 0.5,
                'execution_cr': 0.5,
                'execution_xr': 0.5,
                'execution_surprise': 0.5
            }
    
    async def _contribute_to_global_execution_theta(self, phi: float, rho: float) -> float:
        """Contribute to global execution θ field"""
        try:
            # Get current global θ value
            current_theta = await self._get_current_global_theta()
            
            # Calculate contribution based on φ and ρ
            contribution = (phi + rho) / 2.0
            
            # Update global θ with weighted contribution
            new_theta = current_theta * 0.9 + contribution * 0.1  # 10% influence
            
            # Store updated θ value
            await self._store_global_theta(new_theta)
            
            return new_theta
            
        except Exception as e:
            logger.error(f"Error contributing to global execution θ: {e}")
            return 0.5
    
    def _calculate_pattern_similarity(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> float:
        """Calculate similarity between two execution patterns"""
        try:
            # Compare key execution metrics
            similarities = []
            
            # Execution quality similarity
            if 'execution_quality' in pattern1 and 'execution_quality' in pattern2:
                quality_sim = 1.0 - abs(pattern1['execution_quality'] - pattern2['execution_quality'])
                similarities.append(quality_sim)
            
            # Slippage similarity
            if 'slippage' in pattern1 and 'slippage' in pattern2:
                slippage_sim = 1.0 - min(abs(pattern1['slippage'] - pattern2['slippage']), 1.0)
                similarities.append(slippage_sim)
            
            # Fill time similarity
            if 'fill_time' in pattern1 and 'fill_time' in pattern2:
                time_sim = 1.0 - min(abs(pattern1['fill_time'] - pattern2['fill_time']) / 10.0, 1.0)
                similarities.append(time_sim)
            
            # Strategy similarity
            if pattern1.get('execution_strategy') == pattern2.get('execution_strategy'):
                similarities.append(1.0)
            else:
                similarities.append(0.0)
            
            return np.mean(similarities) if similarities else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating pattern similarity: {e}")
            return 0.5
    
    def _calculate_pattern_consistency(self, pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> float:
        """Calculate consistency between consecutive execution patterns"""
        try:
            # Consistency is based on how similar patterns are over time
            similarity = self._calculate_pattern_similarity(pattern1, pattern2)
            
            # Add temporal consistency factor
            temporal_factor = 0.8  # Assume 80% temporal consistency
            
            return similarity * temporal_factor
            
        except Exception as e:
            logger.error(f"Error calculating pattern consistency: {e}")
            return 0.5
    
    def _calculate_execution_surprise(self, execution_data: Dict[str, Any], phi: float, rho: float) -> float:
        """Calculate execution surprise factor"""
        try:
            # Surprise is inversely related to resonance
            expected_resonance = (phi + rho) / 2.0
            surprise = 1.0 - expected_resonance
            
            # Add execution-specific surprise factors
            if execution_data.get('slippage', 0) > 0.01:  # High slippage
                surprise += 0.2
            
            if execution_data.get('fill_time', 0) > 5.0:  # Slow fill
                surprise += 0.1
            
            return max(0.0, min(1.0, surprise))
            
        except Exception as e:
            logger.error(f"Error calculating execution surprise: {e}")
            return 0.5
    
    def _calculate_execution_resonance_boost(self, resonance_metrics: ExecutionResonanceMetrics) -> float:
        """Calculate resonance boost for execution score enhancement"""
        try:
            # Boost is based on φ, ρ, and telemetry
            phi_boost = resonance_metrics.phi * 0.4
            rho_boost = resonance_metrics.rho * 0.3
            telemetry_boost = (
                resonance_metrics.execution_sr * 0.1 +
                resonance_metrics.execution_cr * 0.1 +
                resonance_metrics.execution_xr * 0.1
            )
            
            total_boost = phi_boost + rho_boost + telemetry_boost
            return max(0.0, min(1.0, total_boost))
            
        except Exception as e:
            logger.error(f"Error calculating execution resonance boost: {e}")
            return 0.0
    
    def _cache_resonance_metrics(self, execution_id: str, metrics: ExecutionResonanceMetrics):
        """Cache resonance metrics for future use"""
        if execution_id:
            self.resonance_cache[execution_id] = metrics
    
    def _get_default_resonance_metrics(self) -> Dict[str, float]:
        """Get default resonance metrics when calculation fails"""
        return {
            'phi': 0.5,
            'rho': 0.5,
            'theta': 0.5,
            'execution_sr': 0.5,
            'execution_cr': 0.5,
            'execution_xr': 0.5,
            'execution_surprise': 0.5,
            'timestamp': datetime.now().isoformat()
        }
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _query_similar_execution_strands(self, execution_type: str) -> List[Dict[str, Any]]:
        """Query similar execution strands from AD_strands table"""
        # Implementation will follow existing database patterns
        return []
    
    async def _get_historical_execution_patterns(self, execution_pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get historical execution patterns for comparison"""
        # Implementation will follow existing database patterns
        return []
    
    async def _get_recent_execution_patterns(self, execution_pattern: Dict[str, Any], hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent execution patterns for feedback analysis"""
        # Implementation will follow existing database patterns
        return []
    
    async def _calculate_execution_success_rate(self, execution_data: Dict[str, Any]) -> float:
        """Calculate execution success rate"""
        # Implementation will follow existing patterns
        return 0.8
    
    async def _calculate_execution_consistency_rate(self, execution_data: Dict[str, Any]) -> float:
        """Calculate execution consistency rate"""
        # Implementation will follow existing patterns
        return 0.7
    
    async def _calculate_execution_cross_correlation_rate(self, execution_data: Dict[str, Any]) -> float:
        """Calculate execution cross-correlation rate"""
        # Implementation will follow existing patterns
        return 0.6
    
    async def _get_base_execution_score(self, execution_strand_id: str) -> float:
        """Get base execution score from strand"""
        # Implementation will follow existing database patterns
        return 0.5
    
    async def _get_strand_resonance_metrics(self, execution_strand_id: str) -> Optional[ExecutionResonanceMetrics]:
        """Get resonance metrics for a specific strand"""
        # Implementation will follow existing database patterns
        return None
    
    async def _get_current_global_theta(self) -> float:
        """Get current global θ value"""
        # Implementation will follow existing database patterns
        return 0.5
    
    async def _store_global_theta(self, theta: float):
        """Store updated global θ value"""
        # Implementation will follow existing database patterns
        pass
    
    async def _calculate_execution_cluster_resonance(self, similar_strands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate execution cluster resonance"""
        # Implementation will follow existing patterns
        return []
