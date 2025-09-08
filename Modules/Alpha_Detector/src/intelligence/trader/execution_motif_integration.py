"""
Execution Motif Integration

Handles execution motif integration for organic pattern evolution.
Enables Trader agents to work with and create execution motif strands for
organic pattern development and evolution.

Key Features:
- Execution motif creation from detected patterns
- Execution motif enhancement with new evidence
- Execution motif family queries for pattern discovery
- Organic pattern evolution through motif integration
- Cross-scale pattern recognition and synthesis
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMotifType(Enum):
    """Types of execution motifs for pattern classification"""
    EXECUTION_QUALITY_PATTERN = "execution_quality_pattern"
    VENUE_SELECTION_PATTERN = "venue_selection_pattern"
    TIMING_OPTIMIZATION_PATTERN = "timing_optimization_pattern"
    POSITION_SIZING_PATTERN = "position_sizing_pattern"
    MARKET_IMPACT_PATTERN = "market_impact_pattern"
    EXECUTION_STRATEGY_PATTERN = "execution_strategy_pattern"
    CROSS_VENUE_ARBITRAGE_PATTERN = "cross_venue_arbitrage_pattern"
    RISK_MANAGEMENT_PATTERN = "risk_management_pattern"


@dataclass
class ExecutionMotifData:
    """Execution motif data for organic pattern evolution"""
    motif_id: str
    motif_type: ExecutionMotifType
    pattern_invariants: List[str]
    failure_conditions: List[str]
    mechanism_hypotheses: List[str]
    lineage_information: Dict[str, Any]
    resonance_metrics: Dict[str, float]
    evidence_count: int
    success_rate: float
    created_at: datetime
    last_updated: datetime


class ExecutionMotifIntegration:
    """Handles execution motif integration for organic pattern evolution"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.motif_cache = {}
        self.pattern_families = {}
        
    async def create_execution_motif_from_pattern(self, execution_pattern_data: Dict[str, Any]) -> str:
        """
        Create execution motif strand from detected execution pattern for organic evolution
        
        Args:
            execution_pattern_data: Execution pattern data to create motif from
            
        Returns:
            Motif ID of the created execution motif strand
        """
        try:
            # Extract execution pattern invariants
            invariants = await self._extract_execution_pattern_invariants(execution_pattern_data)
            
            # Identify execution failure conditions
            failure_conditions = await self._identify_execution_failure_conditions(execution_pattern_data)
            
            # Create execution mechanism hypothesis
            mechanism_hypotheses = await self._create_execution_mechanism_hypotheses(
                execution_pattern_data, invariants, failure_conditions
            )
            
            # Generate execution lineage information
            lineage_info = await self._generate_execution_lineage_information(execution_pattern_data)
            
            # Calculate resonance metrics for the motif
            resonance_metrics = await self._calculate_motif_resonance_metrics(
                execution_pattern_data, invariants, failure_conditions
            )
            
            # Create execution motif strand
            motif_strand = {
                'module': 'trader',
                'kind': 'execution_motif',
                'content': {
                    'motif_type': self._determine_motif_type(execution_pattern_data),
                    'pattern_invariants': invariants,
                    'failure_conditions': failure_conditions,
                    'mechanism_hypotheses': mechanism_hypotheses,
                    'lineage_information': lineage_info,
                    'resonance_metrics': resonance_metrics,
                    'evidence_count': 1,
                    'success_rate': execution_pattern_data.get('success_rate', 0.5),
                    'creation_context': execution_pattern_data.get('context', {}),
                    'motif_family': self._determine_motif_family(execution_pattern_data)
                },
                'tags': [
                    'trader:execution_motif',
                    'trader:pattern_evolution',
                    'trader:organic_intelligence',
                    f'trader:motif_type:{self._determine_motif_type(execution_pattern_data).value}',
                    f'trader:motif_family:{self._determine_motif_family(execution_pattern_data)}'
                ],
                'sig_confidence': resonance_metrics.get('phi', 0.5),
                'outcome_score': execution_pattern_data.get('success_rate', 0.5),
                'created_at': datetime.now().isoformat()
            }
            
            # Publish as execution motif strand to AD_strands with resonance values
            motif_id = await self._publish_motif_strand_to_database(motif_strand)
            
            # Cache motif data
            self._cache_motif_data(motif_id, motif_strand)
            
            logger.info(f"Created execution motif: {motif_id}, "
                       f"type: {motif_strand['content']['motif_type'].value}, "
                       f"invariants: {len(invariants)}")
            
            return motif_id
            
        except Exception as e:
            logger.error(f"Error creating execution motif from pattern: {e}")
            return ""
    
    async def enhance_existing_execution_motif(self, execution_motif_id: str, new_execution_evidence: Dict[str, Any]):
        """
        Enhance existing execution motif with new evidence for organic growth
        
        Args:
            execution_motif_id: ID of the existing execution motif
            new_execution_evidence: New evidence to add to the motif
        """
        try:
            # Find existing execution motif strand in AD_strands
            existing_motif = await self._get_existing_motif_strand(execution_motif_id)
            
            if not existing_motif:
                logger.warning(f"Existing motif not found: {execution_motif_id}")
                return
            
            # Add new execution evidence references
            updated_invariants = await self._update_motif_invariants(
                existing_motif['content']['pattern_invariants'], new_execution_evidence
            )
            
            # Update execution invariants if needed
            updated_failure_conditions = await self._update_failure_conditions(
                existing_motif['content']['failure_conditions'], new_execution_evidence
            )
            
            # Update execution telemetry and resonance
            updated_resonance = await self._update_motif_resonance(
                existing_motif['content']['resonance_metrics'], new_execution_evidence
            )
            
            # Create enhancement strand
            enhancement_strand = {
                'module': 'trader',
                'kind': 'motif_enhancement',
                'content': {
                    'original_motif_id': execution_motif_id,
                    'new_evidence': new_execution_evidence,
                    'updated_invariants': updated_invariants,
                    'updated_failure_conditions': updated_failure_conditions,
                    'updated_resonance': updated_resonance,
                    'enhancement_type': 'evidence_addition',
                    'evidence_impact': self._calculate_evidence_impact(new_execution_evidence)
                },
                'tags': [
                    'trader:motif_enhancement',
                    'trader:pattern_evolution',
                    f'trader:motif_id:{execution_motif_id}',
                    'trader:organic_growth'
                ],
                'sig_confidence': updated_resonance.get('phi', 0.5),
                'outcome_score': new_execution_evidence.get('success_rate', 0.5),
                'created_at': datetime.now().isoformat()
            }
            
            # Publish execution enhancement strand to AD_strands
            enhancement_id = await self._publish_strand_to_database(enhancement_strand)
            
            # Update motif cache
            self._update_motif_cache(execution_motif_id, enhancement_strand)
            
            logger.info(f"Enhanced execution motif: {execution_motif_id}, "
                       f"enhancement: {enhancement_id}, "
                       f"evidence impact: {enhancement_strand['content']['evidence_impact']:.3f}")
            
        except Exception as e:
            logger.error(f"Error enhancing existing execution motif: {e}")
    
    async def query_execution_motif_families(self, execution_type: str) -> List[Dict[str, Any]]:
        """
        Query relevant execution motif families for organic pattern discovery
        
        Args:
            execution_type: Type of execution to find motif families for
            
        Returns:
            List of relevant execution motifs with resonance scores
        """
        try:
            # Search execution motif strands by family in AD_strands
            motif_families = await self._search_motif_families_by_type(execution_type)
            
            if not motif_families:
                logger.warning(f"No motif families found for execution type: {execution_type}")
                return []
            
            # Calculate family resonance scores
            family_resonance = await self._calculate_family_resonance_scores(motif_families)
            
            # Include execution success rates and telemetry
            enriched_families = await self._enrich_families_with_telemetry(
                motif_families, family_resonance
            )
            
            # Sort by resonance score
            sorted_families = sorted(
                enriched_families, 
                key=lambda x: x.get('resonance_score', 0), 
                reverse=True
            )
            
            logger.info(f"Found {len(sorted_families)} motif families for {execution_type}, "
                       f"top resonance: {sorted_families[0].get('resonance_score', 0):.3f}" if sorted_families else "No families found")
            
            return sorted_families
            
        except Exception as e:
            logger.error(f"Error querying execution motif families: {e}")
            return []
    
    async def _extract_execution_pattern_invariants(self, execution_pattern_data: Dict[str, Any]) -> List[str]:
        """Extract execution pattern invariants that remain consistent across scenarios"""
        try:
            invariants = []
            
            # Extract execution quality invariants
            if 'execution_quality' in execution_pattern_data:
                quality = execution_pattern_data['execution_quality']
                if quality > 0.8:
                    invariants.append("High execution quality maintained across scenarios")
                elif quality < 0.3:
                    invariants.append("Low execution quality consistent pattern")
            
            # Extract venue selection invariants
            if 'venue' in execution_pattern_data:
                venue = execution_pattern_data['venue']
                invariants.append(f"Consistent venue selection: {venue}")
            
            # Extract timing invariants
            if 'fill_time' in execution_pattern_data:
                fill_time = execution_pattern_data['fill_time']
                if fill_time < 2.0:
                    invariants.append("Fast execution timing pattern")
                elif fill_time > 10.0:
                    invariants.append("Slow execution timing pattern")
            
            # Extract market condition invariants
            if 'market_conditions' in execution_pattern_data:
                conditions = execution_pattern_data['market_conditions']
                if conditions.get('volatility', 0) > 0.5:
                    invariants.append("High volatility market condition pattern")
                if conditions.get('liquidity', 0) > 0.8:
                    invariants.append("High liquidity market condition pattern")
            
            # Extract strategy invariants
            if 'execution_strategy' in execution_pattern_data:
                strategy = execution_pattern_data['execution_strategy']
                invariants.append(f"Consistent execution strategy: {strategy}")
            
            return invariants
            
        except Exception as e:
            logger.error(f"Error extracting execution pattern invariants: {e}")
            return []
    
    async def _identify_execution_failure_conditions(self, execution_pattern_data: Dict[str, Any]) -> List[str]:
        """Identify execution failure conditions that lead to pattern failure"""
        try:
            failure_conditions = []
            
            # High slippage failure condition
            if 'slippage' in execution_pattern_data:
                slippage = execution_pattern_data['slippage']
                if slippage > 0.01:  # 1% slippage
                    failure_conditions.append("High slippage leads to execution failure")
            
            # Slow fill time failure condition
            if 'fill_time' in execution_pattern_data:
                fill_time = execution_pattern_data['fill_time']
                if fill_time > 30.0:  # 30 seconds
                    failure_conditions.append("Slow fill time leads to execution failure")
            
            # High price impact failure condition
            if 'price_impact' in execution_pattern_data:
                price_impact = execution_pattern_data['price_impact']
                if price_impact > 0.005:  # 0.5% impact
                    failure_conditions.append("High price impact leads to execution failure")
            
            # Market condition failure conditions
            if 'market_conditions' in execution_pattern_data:
                conditions = execution_pattern_data['market_conditions']
                if conditions.get('volatility', 0) > 0.8:
                    failure_conditions.append("Extreme volatility leads to execution failure")
                if conditions.get('liquidity', 0) < 0.2:
                    failure_conditions.append("Low liquidity leads to execution failure")
            
            # Venue-specific failure conditions
            if 'venue' in execution_pattern_data:
                venue = execution_pattern_data['venue']
                if venue == 'low_liquidity_venue':
                    failure_conditions.append("Low liquidity venue leads to execution failure")
            
            return failure_conditions
            
        except Exception as e:
            logger.error(f"Error identifying execution failure conditions: {e}")
            return []
    
    async def _create_execution_mechanism_hypotheses(self, execution_pattern_data: Dict[str, Any], 
                                                   invariants: List[str], failure_conditions: List[str]) -> List[str]:
        """Create execution mechanism hypotheses for pattern emergence"""
        try:
            hypotheses = []
            
            # Quality-based mechanism hypotheses
            if any("High execution quality" in inv for inv in invariants):
                hypotheses.append("High execution quality results from optimal venue selection and timing")
            
            if any("Low execution quality" in inv for inv in invariants):
                hypotheses.append("Low execution quality results from poor venue selection or market timing")
            
            # Timing-based mechanism hypotheses
            if any("Fast execution timing" in inv for inv in invariants):
                hypotheses.append("Fast execution timing results from high liquidity venues and optimal order sizing")
            
            if any("Slow execution timing" in inv for inv in invariants):
                hypotheses.append("Slow execution timing results from low liquidity or large order sizes")
            
            # Market condition mechanism hypotheses
            if any("High volatility" in inv for inv in invariants):
                hypotheses.append("High volatility creates execution opportunities but increases risk")
            
            if any("High liquidity" in inv for inv in invariants):
                hypotheses.append("High liquidity enables efficient execution with minimal market impact")
            
            # Failure condition mechanism hypotheses
            if any("High slippage" in fc for fc in failure_conditions):
                hypotheses.append("High slippage occurs when market moves against execution during fill time")
            
            if any("Low liquidity" in fc for fc in failure_conditions):
                hypotheses.append("Low liquidity creates execution challenges and increases market impact")
            
            # Strategy-based mechanism hypotheses
            if 'execution_strategy' in execution_pattern_data:
                strategy = execution_pattern_data['execution_strategy']
                hypotheses.append(f"{strategy} strategy effectiveness depends on market conditions and order size")
            
            return hypotheses
            
        except Exception as e:
            logger.error(f"Error creating execution mechanism hypotheses: {e}")
            return []
    
    async def _generate_execution_lineage_information(self, execution_pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution lineage information for pattern tracking"""
        try:
            lineage_info = {
                'pattern_source': execution_pattern_data.get('source', 'unknown'),
                'creation_timestamp': datetime.now().isoformat(),
                'parent_patterns': execution_pattern_data.get('parent_patterns', []),
                'evolution_history': [],
                'related_motifs': [],
                'cross_references': []
            }
            
            # Add agent information if available
            if 'agent_name' in execution_pattern_data:
                lineage_info['creating_agent'] = execution_pattern_data['agent_name']
            
            # Add market context
            if 'market_conditions' in execution_pattern_data:
                lineage_info['market_context'] = execution_pattern_data['market_conditions']
            
            # Add execution context
            if 'execution_context' in execution_pattern_data:
                lineage_info['execution_context'] = execution_pattern_data['execution_context']
            
            return lineage_info
            
        except Exception as e:
            logger.error(f"Error generating execution lineage information: {e}")
            return {}
    
    async def _calculate_motif_resonance_metrics(self, execution_pattern_data: Dict[str, Any], 
                                               invariants: List[str], failure_conditions: List[str]) -> Dict[str, float]:
        """Calculate resonance metrics for the execution motif"""
        try:
            # Base resonance from pattern quality
            base_resonance = execution_pattern_data.get('success_rate', 0.5)
            
            # Boost from invariant strength
            invariant_boost = min(len(invariants) * 0.1, 0.3)  # Max 30% boost
            
            # Boost from mechanism hypotheses
            hypothesis_boost = min(len(execution_pattern_data.get('mechanism_hypotheses', [])) * 0.05, 0.2)  # Max 20% boost
            
            # Penalty from failure conditions
            failure_penalty = min(len(failure_conditions) * 0.05, 0.2)  # Max 20% penalty
            
            # Calculate final resonance
            phi = max(0.0, min(1.0, base_resonance + invariant_boost + hypothesis_boost - failure_penalty))
            rho = phi * 0.9  # Slightly lower for feedback loops
            theta = (phi + rho) / 2.0  # Average for global field
            
            return {
                'phi': phi,
                'rho': rho,
                'theta': theta,
                'invariant_strength': len(invariants),
                'hypothesis_count': len(execution_pattern_data.get('mechanism_hypotheses', [])),
                'failure_condition_count': len(failure_conditions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating motif resonance metrics: {e}")
            return {'phi': 0.5, 'rho': 0.5, 'theta': 0.5}
    
    def _determine_motif_type(self, execution_pattern_data: Dict[str, Any]) -> ExecutionMotifType:
        """Determine the type of execution motif based on pattern data"""
        try:
            # Check for specific pattern indicators
            if 'execution_quality' in execution_pattern_data:
                return ExecutionMotifType.EXECUTION_QUALITY_PATTERN
            
            if 'venue' in execution_pattern_data:
                return ExecutionMotifType.VENUE_SELECTION_PATTERN
            
            if 'fill_time' in execution_pattern_data:
                return ExecutionMotifType.TIMING_OPTIMIZATION_PATTERN
            
            if 'position_size' in execution_pattern_data:
                return ExecutionMotifType.POSITION_SIZING_PATTERN
            
            if 'price_impact' in execution_pattern_data:
                return ExecutionMotifType.MARKET_IMPACT_PATTERN
            
            if 'execution_strategy' in execution_pattern_data:
                return ExecutionMotifType.EXECUTION_STRATEGY_PATTERN
            
            # Default to execution strategy pattern
            return ExecutionMotifType.EXECUTION_STRATEGY_PATTERN
            
        except Exception as e:
            logger.error(f"Error determining motif type: {e}")
            return ExecutionMotifType.EXECUTION_STRATEGY_PATTERN
    
    def _determine_motif_family(self, execution_pattern_data: Dict[str, Any]) -> str:
        """Determine the motif family for grouping related patterns"""
        try:
            # Group by execution strategy
            if 'execution_strategy' in execution_pattern_data:
                return f"strategy_{execution_pattern_data['execution_strategy']}"
            
            # Group by venue
            if 'venue' in execution_pattern_data:
                return f"venue_{execution_pattern_data['venue']}"
            
            # Group by market conditions
            if 'market_conditions' in execution_pattern_data:
                conditions = execution_pattern_data['market_conditions']
                if conditions.get('volatility', 0) > 0.5:
                    return "high_volatility"
                elif conditions.get('liquidity', 0) > 0.8:
                    return "high_liquidity"
                else:
                    return "normal_conditions"
            
            return "general_execution"
            
        except Exception as e:
            logger.error(f"Error determining motif family: {e}")
            return "general_execution"
    
    def _calculate_evidence_impact(self, new_execution_evidence: Dict[str, Any]) -> float:
        """Calculate the impact of new evidence on motif evolution"""
        try:
            impact = 0.0
            
            # Success rate impact
            if 'success_rate' in new_execution_evidence:
                success_rate = new_execution_evidence['success_rate']
                impact += abs(success_rate - 0.5) * 0.5  # Distance from neutral
            
            # Quality impact
            if 'execution_quality' in new_execution_evidence:
                quality = new_execution_evidence['execution_quality']
                impact += abs(quality - 0.5) * 0.3  # Distance from neutral
            
            # Novelty impact
            if 'novelty_score' in new_execution_evidence:
                novelty = new_execution_evidence['novelty_score']
                impact += novelty * 0.2
            
            return max(0.0, min(1.0, impact))
            
        except Exception as e:
            logger.error(f"Error calculating evidence impact: {e}")
            return 0.0
    
    def _cache_motif_data(self, motif_id: str, motif_strand: Dict[str, Any]):
        """Cache motif data for quick access"""
        self.motif_cache[motif_id] = {
            'strand': motif_strand,
            'cached_at': datetime.now(),
            'access_count': 0
        }
    
    def _update_motif_cache(self, motif_id: str, enhancement_strand: Dict[str, Any]):
        """Update motif cache with enhancement data"""
        if motif_id in self.motif_cache:
            self.motif_cache[motif_id]['enhancements'] = self.motif_cache[motif_id].get('enhancements', [])
            self.motif_cache[motif_id]['enhancements'].append(enhancement_strand)
            self.motif_cache[motif_id]['last_updated'] = datetime.now()
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _publish_motif_strand_to_database(self, motif_strand: Dict[str, Any]) -> str:
        """Publish motif strand to AD_strands table"""
        # Implementation will follow existing database patterns
        return f"motif_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _get_existing_motif_strand(self, motif_id: str) -> Optional[Dict[str, Any]]:
        """Get existing motif strand from AD_strands table"""
        # Implementation will follow existing database patterns
        return None
    
    async def _publish_strand_to_database(self, strand: Dict[str, Any]) -> str:
        """Publish strand to AD_strands table"""
        # Implementation will follow existing database patterns
        return f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _search_motif_families_by_type(self, execution_type: str) -> List[Dict[str, Any]]:
        """Search motif families by execution type in AD_strands"""
        # Implementation will follow existing database patterns
        return []
    
    async def _calculate_family_resonance_scores(self, motif_families: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate resonance scores for motif families"""
        # Implementation will follow existing patterns
        return {}
    
    async def _enrich_families_with_telemetry(self, motif_families: List[Dict[str, Any]], 
                                            family_resonance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Enrich motif families with telemetry data"""
        # Implementation will follow existing patterns
        return motif_families
    
    async def _update_motif_invariants(self, existing_invariants: List[str], 
                                     new_evidence: Dict[str, Any]) -> List[str]:
        """Update motif invariants with new evidence"""
        # Implementation will follow existing patterns
        return existing_invariants
    
    async def _update_failure_conditions(self, existing_conditions: List[str], 
                                       new_evidence: Dict[str, Any]) -> List[str]:
        """Update failure conditions with new evidence"""
        # Implementation will follow existing patterns
        return existing_conditions
    
    async def _update_motif_resonance(self, existing_resonance: Dict[str, float], 
                                    new_evidence: Dict[str, Any]) -> Dict[str, float]:
        """Update motif resonance with new evidence"""
        # Implementation will follow existing patterns
        return existing_resonance
