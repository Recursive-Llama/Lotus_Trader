"""
Execution Uncertainty Handler

Handles execution uncertainty-driven curiosity for organic exploration.
Embraces execution uncertainty as the default state and valuable exploration driver.

Key Philosophy: Execution uncertainty is the default state - being unsure about 
execution is valuable information that drives exploration. Low confidence execution 
assessments are not failures, they are execution curiosity opportunities.

Key Features:
- Execution uncertainty detection and analysis
- Execution uncertainty strand publishing to AD_strands
- Execution uncertainty resolution through organic exploration
- Positive framing of uncertainty as learning opportunity
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionUncertaintyType(Enum):
    """Types of execution uncertainty that drive exploration"""
    EXECUTION_QUALITY = "execution_quality"
    VENUE_SELECTION = "venue_selection"
    TIMING_OPTIMIZATION = "timing_optimization"
    POSITION_SIZING = "position_sizing"
    MARKET_IMPACT = "market_impact"
    EXECUTION_STRATEGY = "execution_strategy"
    CROSS_VENUE_ARBITRAGE = "cross_venue_arbitrage"
    RISK_MANAGEMENT = "risk_management"


@dataclass
class ExecutionUncertaintyData:
    """Execution uncertainty data for organic exploration"""
    uncertainty_type: ExecutionUncertaintyType
    confidence_level: float  # 0.0 = very uncertain, 1.0 = very confident
    uncertainty_factors: List[str]
    exploration_priority: float  # 0.0 = low priority, 1.0 = high priority
    resolution_suggestions: List[str]
    context_data: Dict[str, Any]
    timestamp: datetime


class ExecutionUncertaintyHandler:
    """Handles execution uncertainty-driven curiosity for organic exploration"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.uncertainty_threshold = 0.7  # Below this is considered uncertain
        self.exploration_threshold = 0.3  # Below this triggers active exploration
        
    async def detect_execution_uncertainty(self, execution_analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect execution uncertainty that drives organic exploration - execution uncertainty is valuable!
        
        Args:
            execution_analysis_result: Results from execution analysis
            
        Returns:
            Dict containing uncertainty analysis and exploration recommendations
        """
        try:
            # Assess execution pattern clarity (uncertainty is good if identified)
            pattern_clarity = await self._assess_execution_pattern_clarity(execution_analysis_result)
            
            # Evaluate execution data sufficiency (insufficient execution data = exploration opportunity)
            data_sufficiency = await self._evaluate_execution_data_sufficiency(execution_analysis_result)
            
            # Calculate execution confidence levels (low confidence = execution curiosity driver)
            confidence_levels = await self._calculate_execution_confidence_levels(execution_analysis_result)
            
            # Identify execution uncertainty types that drive exploration
            uncertainty_types = await self._identify_execution_uncertainty_types(
                execution_analysis_result, confidence_levels
            )
            
            # Treat execution uncertainty as DEFAULT state, not exception
            uncertainty_analysis = {
                'pattern_clarity': pattern_clarity,
                'data_sufficiency': data_sufficiency,
                'confidence_levels': confidence_levels,
                'uncertainty_types': uncertainty_types,
                'overall_uncertainty': self._calculate_overall_uncertainty(confidence_levels),
                'exploration_opportunities': self._identify_exploration_opportunities(uncertainty_types),
                'uncertainty_is_valuable': True,  # Always true - uncertainty drives learning
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Detected execution uncertainty: {len(uncertainty_types)} types, "
                       f"overall uncertainty: {uncertainty_analysis['overall_uncertainty']:.3f}")
            
            return uncertainty_analysis
            
        except Exception as e:
            logger.error(f"Error detecting execution uncertainty: {e}")
            return self._get_default_uncertainty_analysis()
    
    async def publish_execution_uncertainty_strand(self, execution_uncertainty_data: Dict[str, Any]) -> str:
        """
        Publish execution uncertainty as specialized strand for organic resolution
        
        Args:
            execution_uncertainty_data: Uncertainty data to publish
            
        Returns:
            Strand ID of the published uncertainty strand
        """
        try:
            # Create execution uncertainty strand with positive framing
            uncertainty_strand = {
                'module': 'trader',
                'kind': 'execution_uncertainty',
                'content': {
                    'uncertainty_analysis': execution_uncertainty_data,
                    'exploration_opportunities': execution_uncertainty_data.get('exploration_opportunities', []),
                    'resolution_suggestions': self._generate_resolution_suggestions(execution_uncertainty_data),
                    'positive_framing': {
                        'uncertainty_is_learning': True,
                        'exploration_drives_growth': True,
                        'low_confidence_is_opportunity': True
                    }
                },
                'tags': [
                    'trader:execution_uncertainty',
                    'trader:exploration_opportunity',
                    'trader:learning_driver',
                    'cil:strategic_contribution'
                ],
                'sig_confidence': 1.0 - execution_uncertainty_data.get('overall_uncertainty', 0.5),  # Inverted for confidence
                'outcome_score': 0.0,  # Will be updated as uncertainty is resolved
                'created_at': datetime.now().isoformat()
            }
            
            # Set execution uncertainty type and exploration priority
            uncertainty_type = execution_uncertainty_data.get('primary_uncertainty_type', 'general')
            exploration_priority = execution_uncertainty_data.get('exploration_priority', 0.5)
            
            uncertainty_strand['content']['uncertainty_type'] = uncertainty_type
            uncertainty_strand['content']['exploration_priority'] = exploration_priority
            
            # Tag for natural clustering and resolution
            uncertainty_strand['tags'].extend([
                f'trader:uncertainty_type:{uncertainty_type}',
                f'trader:priority:{self._get_priority_level(exploration_priority)}'
            ])
            
            # Include execution resolution suggestions and exploration directions
            uncertainty_strand['content']['exploration_directions'] = self._generate_exploration_directions(
                execution_uncertainty_data
            )
            
            # Emphasize that execution uncertainty is valuable information
            uncertainty_strand['content']['value_proposition'] = {
                'uncertainty_drives_learning': True,
                'exploration_improves_system': True,
                'low_confidence_creates_opportunity': True,
                'resolution_contributes_to_doctrine': True
            }
            
            # Publish to AD_strands table
            strand_id = await self._publish_strand_to_database(uncertainty_strand)
            
            logger.info(f"Published execution uncertainty strand: {strand_id}, "
                       f"type: {uncertainty_type}, priority: {exploration_priority:.3f}")
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error publishing execution uncertainty strand: {e}")
            return ""
    
    async def handle_execution_uncertainty_resolution(self, execution_uncertainty_id: str, resolution_data: Dict[str, Any]):
        """
        Handle execution uncertainty resolution through organic exploration
        
        Args:
            execution_uncertainty_id: ID of the uncertainty strand to resolve
            resolution_data: Data from exploration and resolution attempts
        """
        try:
            # Update execution uncertainty strand with resolution progress
            await self._update_uncertainty_strand_progress(execution_uncertainty_id, resolution_data)
            
            # Execute execution exploration actions based on uncertainty
            exploration_results = await self._execute_execution_exploration_actions(
                execution_uncertainty_id, resolution_data
            )
            
            # Track execution resolution progress and learning
            learning_insights = await self._track_execution_resolution_learning(
                execution_uncertainty_id, exploration_results
            )
            
            # Report execution resolution results and new insights gained
            await self._report_execution_resolution_results(
                execution_uncertainty_id, exploration_results, learning_insights
            )
            
            # Celebrate execution uncertainty as learning opportunity
            await self._celebrate_uncertainty_learning(execution_uncertainty_id, learning_insights)
            
            logger.info(f"Handled execution uncertainty resolution: {execution_uncertainty_id}, "
                       f"insights: {len(learning_insights)}")
            
        except Exception as e:
            logger.error(f"Error handling execution uncertainty resolution: {e}")
    
    async def _assess_execution_pattern_clarity(self, execution_analysis_result: Dict[str, Any]) -> float:
        """Assess how clear the execution pattern is (uncertainty is good if identified)"""
        try:
            # Analyze execution pattern clarity indicators
            clarity_indicators = []
            
            # Execution quality clarity
            if 'execution_quality' in execution_analysis_result:
                quality_variance = execution_analysis_result.get('execution_quality_variance', 0.1)
                clarity_indicators.append(1.0 - quality_variance)
            
            # Venue selection clarity
            if 'venue_selection' in execution_analysis_result:
                venue_confidence = execution_analysis_result.get('venue_confidence', 0.5)
                clarity_indicators.append(venue_confidence)
            
            # Timing optimization clarity
            if 'timing_optimization' in execution_analysis_result:
                timing_confidence = execution_analysis_result.get('timing_confidence', 0.5)
                clarity_indicators.append(timing_confidence)
            
            # Market impact clarity
            if 'market_impact' in execution_analysis_result:
                impact_confidence = execution_analysis_result.get('impact_confidence', 0.5)
                clarity_indicators.append(impact_confidence)
            
            # Return average clarity (lower = more uncertain = more exploration opportunity)
            return sum(clarity_indicators) / len(clarity_indicators) if clarity_indicators else 0.5
            
        except Exception as e:
            logger.error(f"Error assessing execution pattern clarity: {e}")
            return 0.5
    
    async def _evaluate_execution_data_sufficiency(self, execution_analysis_result: Dict[str, Any]) -> float:
        """Evaluate if execution data is sufficient (insufficient = exploration opportunity)"""
        try:
            # Check data sufficiency indicators
            sufficiency_indicators = []
            
            # Historical execution data
            historical_data_points = execution_analysis_result.get('historical_data_points', 0)
            sufficiency_indicators.append(min(historical_data_points / 100.0, 1.0))
            
            # Market condition coverage
            market_conditions = execution_analysis_result.get('market_conditions_covered', 0)
            sufficiency_indicators.append(min(market_conditions / 10.0, 1.0))
            
            # Venue coverage
            venues_covered = execution_analysis_result.get('venues_covered', 0)
            sufficiency_indicators.append(min(venues_covered / 5.0, 1.0))
            
            # Strategy coverage
            strategies_covered = execution_analysis_result.get('strategies_covered', 0)
            sufficiency_indicators.append(min(strategies_covered / 3.0, 1.0))
            
            # Return average sufficiency (lower = more exploration needed)
            return sum(sufficiency_indicators) / len(sufficiency_indicators) if sufficiency_indicators else 0.5
            
        except Exception as e:
            logger.error(f"Error evaluating execution data sufficiency: {e}")
            return 0.5
    
    async def _calculate_execution_confidence_levels(self, execution_analysis_result: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence levels for different execution aspects"""
        try:
            confidence_levels = {}
            
            # Execution quality confidence
            confidence_levels['execution_quality'] = execution_analysis_result.get(
                'execution_quality_confidence', 0.5
            )
            
            # Venue selection confidence
            confidence_levels['venue_selection'] = execution_analysis_result.get(
                'venue_selection_confidence', 0.5
            )
            
            # Timing optimization confidence
            confidence_levels['timing_optimization'] = execution_analysis_result.get(
                'timing_optimization_confidence', 0.5
            )
            
            # Position sizing confidence
            confidence_levels['position_sizing'] = execution_analysis_result.get(
                'position_sizing_confidence', 0.5
            )
            
            # Market impact confidence
            confidence_levels['market_impact'] = execution_analysis_result.get(
                'market_impact_confidence', 0.5
            )
            
            # Execution strategy confidence
            confidence_levels['execution_strategy'] = execution_analysis_result.get(
                'execution_strategy_confidence', 0.5
            )
            
            return confidence_levels
            
        except Exception as e:
            logger.error(f"Error calculating execution confidence levels: {e}")
            return {}
    
    async def _identify_execution_uncertainty_types(self, execution_analysis_result: Dict[str, Any], 
                                                   confidence_levels: Dict[str, float]) -> List[ExecutionUncertaintyType]:
        """Identify types of execution uncertainty that drive exploration"""
        try:
            uncertainty_types = []
            
            # Check each confidence level for uncertainty
            for aspect, confidence in confidence_levels.items():
                if confidence < self.uncertainty_threshold:
                    try:
                        uncertainty_type = ExecutionUncertaintyType(aspect)
                        uncertainty_types.append(uncertainty_type)
                    except ValueError:
                        # Handle unknown uncertainty types
                        logger.warning(f"Unknown uncertainty type: {aspect}")
            
            # Add general uncertainty if multiple aspects are uncertain
            if len(uncertainty_types) >= 3:
                uncertainty_types.append(ExecutionUncertaintyType.EXECUTION_STRATEGY)
            
            return uncertainty_types
            
        except Exception as e:
            logger.error(f"Error identifying execution uncertainty types: {e}")
            return []
    
    def _calculate_overall_uncertainty(self, confidence_levels: Dict[str, float]) -> float:
        """Calculate overall uncertainty level"""
        try:
            if not confidence_levels:
                return 0.5
            
            # Overall uncertainty is inverse of average confidence
            average_confidence = sum(confidence_levels.values()) / len(confidence_levels)
            return 1.0 - average_confidence
            
        except Exception as e:
            logger.error(f"Error calculating overall uncertainty: {e}")
            return 0.5
    
    def _identify_exploration_opportunities(self, uncertainty_types: List[ExecutionUncertaintyType]) -> List[str]:
        """Identify specific exploration opportunities from uncertainty types"""
        try:
            opportunities = []
            
            for uncertainty_type in uncertainty_types:
                if uncertainty_type == ExecutionUncertaintyType.EXECUTION_QUALITY:
                    opportunities.extend([
                        "Explore different execution algorithms",
                        "Test execution quality metrics",
                        "Analyze execution performance patterns"
                    ])
                elif uncertainty_type == ExecutionUncertaintyType.VENUE_SELECTION:
                    opportunities.extend([
                        "Explore new venue options",
                        "Test venue performance comparison",
                        "Analyze venue selection criteria"
                    ])
                elif uncertainty_type == ExecutionUncertaintyType.TIMING_OPTIMIZATION:
                    opportunities.extend([
                        "Explore timing optimization strategies",
                        "Test market timing algorithms",
                        "Analyze timing impact on execution"
                    ])
                elif uncertainty_type == ExecutionUncertaintyType.POSITION_SIZING:
                    opportunities.extend([
                        "Explore position sizing strategies",
                        "Test dynamic position sizing",
                        "Analyze position sizing impact"
                    ])
                elif uncertainty_type == ExecutionUncertaintyType.MARKET_IMPACT:
                    opportunities.extend([
                        "Explore market impact models",
                        "Test impact minimization strategies",
                        "Analyze impact prediction accuracy"
                    ])
                elif uncertainty_type == ExecutionUncertaintyType.EXECUTION_STRATEGY:
                    opportunities.extend([
                        "Explore new execution strategies",
                        "Test strategy combinations",
                        "Analyze strategy effectiveness"
                    ])
            
            return list(set(opportunities))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error identifying exploration opportunities: {e}")
            return []
    
    def _generate_resolution_suggestions(self, execution_uncertainty_data: Dict[str, Any]) -> List[str]:
        """Generate resolution suggestions for execution uncertainty"""
        try:
            suggestions = []
            
            uncertainty_types = execution_uncertainty_data.get('uncertainty_types', [])
            exploration_opportunities = execution_uncertainty_data.get('exploration_opportunities', [])
            
            # Generate specific suggestions based on uncertainty types
            for uncertainty_type in uncertainty_types:
                if hasattr(uncertainty_type, 'value'):
                    suggestions.append(f"Focus exploration on {uncertainty_type.value}")
            
            # Add general exploration suggestions
            suggestions.extend([
                "Conduct systematic experiments to reduce uncertainty",
                "Gather more data in uncertain areas",
                "Test alternative approaches",
                "Analyze historical patterns for insights",
                "Collaborate with other teams for cross-perspective"
            ])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating resolution suggestions: {e}")
            return ["Conduct systematic exploration to resolve uncertainty"]
    
    def _generate_exploration_directions(self, execution_uncertainty_data: Dict[str, Any]) -> List[str]:
        """Generate specific exploration directions"""
        try:
            directions = []
            
            uncertainty_types = execution_uncertainty_data.get('uncertainty_types', [])
            
            for uncertainty_type in uncertainty_types:
                if hasattr(uncertainty_type, 'value'):
                    directions.append(f"Systematic exploration of {uncertainty_type.value}")
            
            # Add general directions
            directions.extend([
                "Data collection in uncertain areas",
                "Experimental testing of hypotheses",
                "Cross-team collaboration for insights",
                "Historical pattern analysis",
                "Alternative approach testing"
            ])
            
            return directions
            
        except Exception as e:
            logger.error(f"Error generating exploration directions: {e}")
            return ["Systematic exploration and data collection"]
    
    def _get_priority_level(self, exploration_priority: float) -> str:
        """Get priority level string from numeric priority"""
        if exploration_priority >= 0.8:
            return "high"
        elif exploration_priority >= 0.5:
            return "medium"
        else:
            return "low"
    
    def _get_default_uncertainty_analysis(self) -> Dict[str, Any]:
        """Get default uncertainty analysis when detection fails"""
        return {
            'pattern_clarity': 0.5,
            'data_sufficiency': 0.5,
            'confidence_levels': {},
            'uncertainty_types': [],
            'overall_uncertainty': 0.5,
            'exploration_opportunities': [],
            'uncertainty_is_valuable': True,
            'timestamp': datetime.now().isoformat()
        }
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _publish_strand_to_database(self, uncertainty_strand: Dict[str, Any]) -> str:
        """Publish uncertainty strand to AD_strands table"""
        # Implementation will follow existing database patterns
        return f"uncertainty_strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _update_uncertainty_strand_progress(self, uncertainty_id: str, resolution_data: Dict[str, Any]):
        """Update uncertainty strand with resolution progress"""
        # Implementation will follow existing database patterns
        pass
    
    async def _execute_execution_exploration_actions(self, uncertainty_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute exploration actions based on uncertainty"""
        # Implementation will follow existing patterns
        return {}
    
    async def _track_execution_resolution_learning(self, uncertainty_id: str, exploration_results: Dict[str, Any]) -> List[str]:
        """Track learning from uncertainty resolution"""
        # Implementation will follow existing patterns
        return []
    
    async def _report_execution_resolution_results(self, uncertainty_id: str, exploration_results: Dict[str, Any], learning_insights: List[str]):
        """Report resolution results and insights"""
        # Implementation will follow existing patterns
        pass
    
    async def _celebrate_uncertainty_learning(self, uncertainty_id: str, learning_insights: List[str]):
        """Celebrate uncertainty as learning opportunity"""
        # Implementation will follow existing patterns
        pass
