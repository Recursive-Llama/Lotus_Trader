"""
Outcome Analysis Engine for CIL Learning System

This module analyzes prediction outcomes and generates learning insights.
It processes completed predictions to optimize trading strategies and parameters.

Features:
1. Analyze batch of similar predictions for learning
2. Calculate R/R optimization recommendations
3. Generate plan evolution suggestions
4. Identify patterns in successful/failed predictions
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Analysis type for outcome analysis"""
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    RR_OPTIMIZATION = "rr_optimization"
    TIMING_OPTIMIZATION = "timing_optimization"
    RISK_OPTIMIZATION = "risk_optimization"


@dataclass
class PredictionOutcome:
    """Prediction outcome data"""
    prediction_id: str
    symbol: str
    timeframe: str
    pattern_type: str
    strength_range: str
    rr_profile: str
    market_conditions: str
    entry_price: float
    target_price: float
    stop_loss: float
    final_price: float
    outcome: str
    max_drawdown: float
    duration_minutes: int
    success: bool
    rr_achieved: float
    risk_taken: float


@dataclass
class AnalysisResult:
    """Analysis result data"""
    analysis_type: AnalysisType
    cluster_key: str
    sample_size: int
    success_rate: float
    avg_rr: float
    avg_duration: float
    avg_drawdown: float
    recommendations: List[str]
    confidence: float
    created_at: datetime


class OutcomeAnalysisEngine:
    """
    Analyzes prediction outcomes and generates learning insights
    
    This is a new CIL Engine that processes completed predictions
    to optimize trading strategies and parameters.
    """
    
    def __init__(self, supabase_manager, llm_client=None):
        """
        Initialize outcome analysis engine
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for advanced analysis (optional)
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Analysis configuration
        self.min_sample_size = 5
        self.confidence_threshold = 0.7
        self.success_rate_threshold = 0.6
    
    async def analyze_outcome_batch(self, cluster_key: str, predictions: List[Dict]) -> Dict[str, Any]:
        """
        Analyze batch of similar predictions for learning
        
        Args:
            cluster_key: Clustering key for this batch
            predictions: List of prediction dictionaries
            
        Returns:
            Analysis results dictionary
        """
        try:
            if len(predictions) < self.min_sample_size:
                return {
                    'error': f'Insufficient sample size: {len(predictions)} < {self.min_sample_size}',
                    'sample_size': len(predictions)
                }
            
            # Convert predictions to outcome data
            outcomes = [self._convert_to_outcome(pred) for pred in predictions]
            outcomes = [outcome for outcome in outcomes if outcome is not None]
            
            if len(outcomes) < self.min_sample_size:
                return {
                    'error': f'Insufficient valid outcomes: {len(outcomes)} < {self.min_sample_size}',
                    'sample_size': len(outcomes)
                }
            
            # Perform analysis
            analysis_results = []
            
            # Success pattern analysis
            success_analysis = await self._analyze_success_patterns(outcomes, cluster_key)
            if success_analysis:
                analysis_results.append(success_analysis)
            
            # R/R optimization analysis
            rr_analysis = await self._analyze_rr_optimization(outcomes, cluster_key)
            if rr_analysis:
                analysis_results.append(rr_analysis)
            
            # Timing optimization analysis
            timing_analysis = await self._analyze_timing_optimization(outcomes, cluster_key)
            if timing_analysis:
                analysis_results.append(timing_analysis)
            
            # Risk optimization analysis
            risk_analysis = await self._analyze_risk_optimization(outcomes, cluster_key)
            if risk_analysis:
                analysis_results.append(risk_analysis)
            
            return {
                'cluster_key': cluster_key,
                'sample_size': len(outcomes),
                'analysis_results': analysis_results,
                'overall_success_rate': sum(1 for o in outcomes if o.success) / len(outcomes),
                'avg_rr': statistics.mean([o.rr_achieved for o in outcomes]),
                'avg_duration': statistics.mean([o.duration_minutes for o in outcomes]),
                'avg_drawdown': statistics.mean([o.max_drawdown for o in outcomes])
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing outcome batch: {e}")
            return {'error': str(e)}
    
    async def calculate_rr_optimization(self, predictions: List[Dict]) -> Dict[str, Any]:
        """
        Optimize stop loss and target based on historical outcomes
        
        Args:
            predictions: List of prediction dictionaries
            
        Returns:
            R/R optimization recommendations
        """
        try:
            outcomes = [self._convert_to_outcome(pred) for pred in predictions]
            outcomes = [outcome for outcome in outcomes if outcome is not None]
            
            if len(outcomes) < self.min_sample_size:
                return {'error': 'Insufficient data for R/R optimization'}
            
            # Analyze successful vs failed predictions
            successful = [o for o in outcomes if o.success]
            failed = [o for o in outcomes if not o.success]
            
            if not successful or not failed:
                return {'error': 'Need both successful and failed predictions for optimization'}
            
            # Calculate optimal R/R ratios
            successful_rr = [o.rr_achieved for o in successful]
            failed_rr = [o.rr_achieved for o in failed]
            
            avg_successful_rr = statistics.mean(successful_rr)
            avg_failed_rr = statistics.mean(failed_rr)
            
            # Calculate optimal stop loss and target
            avg_entry = statistics.mean([o.entry_price for o in outcomes])
            avg_successful_target = statistics.mean([o.target_price for o in successful])
            avg_failed_stop = statistics.mean([o.stop_loss for o in failed])
            
            # Generate recommendations
            recommendations = []
            
            if avg_successful_rr > 2.0:
                recommendations.append("Current R/R ratio is good, maintain current levels")
            elif avg_successful_rr < 1.5:
                recommendations.append("Increase target prices to improve R/R ratio")
            
            if avg_failed_rr < 0.5:
                recommendations.append("Tighten stop losses to reduce losses")
            elif avg_failed_rr > 1.0:
                recommendations.append("Consider wider stop losses to avoid premature exits")
            
            return {
                'current_avg_rr': statistics.mean([o.rr_achieved for o in outcomes]),
                'successful_avg_rr': avg_successful_rr,
                'failed_avg_rr': avg_failed_rr,
                'recommended_target': avg_successful_target,
                'recommended_stop': avg_failed_stop,
                'recommendations': recommendations,
                'confidence': min(len(outcomes) / 20, 1.0)  # Confidence based on sample size
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating R/R optimization: {e}")
            return {'error': str(e)}
    
    async def generate_plan_evolution(self, cluster_key: str, analysis: Dict) -> Dict[str, Any]:
        """
        Generate evolution recommendations for conditional plans
        
        Args:
            cluster_key: Clustering key for this analysis
            analysis: Analysis results
            
        Returns:
            Plan evolution recommendations
        """
        try:
            if 'error' in analysis:
                return {'error': analysis['error']}
            
            success_rate = analysis.get('overall_success_rate', 0.0)
            avg_rr = analysis.get('avg_rr', 0.0)
            sample_size = analysis.get('sample_size', 0)
            
            # Generate evolution recommendations based on performance
            recommendations = []
            
            if success_rate >= self.success_rate_threshold and avg_rr >= 2.0:
                recommendations.append("Plan is performing well, consider increasing position size")
                recommendations.append("Look for similar patterns in other symbols/timeframes")
            elif success_rate >= self.success_rate_threshold and avg_rr < 1.5:
                recommendations.append("Success rate is good but R/R is low, optimize targets")
                recommendations.append("Consider tightening stop losses")
            elif success_rate < self.success_rate_threshold and avg_rr >= 2.0:
                recommendations.append("R/R is good but success rate is low, improve entry criteria")
                recommendations.append("Add additional filters to reduce false signals")
            else:
                recommendations.append("Plan needs significant improvement")
                recommendations.append("Consider retiring this plan or major revision")
            
            # Add sample size considerations
            if sample_size < 10:
                recommendations.append("Collect more data before making major changes")
            elif sample_size > 50:
                recommendations.append("Sufficient data for confident recommendations")
            
            return {
                'cluster_key': cluster_key,
                'success_rate': success_rate,
                'avg_rr': avg_rr,
                'sample_size': sample_size,
                'recommendations': recommendations,
                'confidence': min(sample_size / 50, 1.0),
                'evolution_priority': self._calculate_evolution_priority(success_rate, avg_rr, sample_size)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating plan evolution: {e}")
            return {'error': str(e)}
    
    def _convert_to_outcome(self, prediction: Dict[str, Any]) -> Optional[PredictionOutcome]:
        """
        Convert prediction dictionary to PredictionOutcome
        
        Args:
            prediction: Prediction dictionary
            
        Returns:
            PredictionOutcome if conversion successful, None otherwise
        """
        try:
            prediction_data = prediction.get('prediction_data', {})
            outcome_data = prediction.get('outcome_data', {})
            
            if not prediction_data or not outcome_data:
                return None
            
            entry_price = prediction_data.get('entry_price', 0.0)
            target_price = prediction_data.get('target_price', 0.0)
            stop_loss = prediction_data.get('stop_loss', 0.0)
            final_price = outcome_data.get('final_price', 0.0)
            
            if not all([entry_price, target_price, stop_loss, final_price]):
                return None
            
            # Calculate metrics
            success = final_price >= target_price
            rr_achieved = (final_price - entry_price) / (entry_price - stop_loss) if entry_price > stop_loss else 0
            risk_taken = (entry_price - stop_loss) / entry_price if entry_price > stop_loss else 0
            
            return PredictionOutcome(
                prediction_id=prediction['id'],
                symbol=prediction.get('symbol', ''),
                timeframe=prediction.get('timeframe', ''),
                pattern_type=prediction.get('pattern_type', ''),
                strength_range=prediction.get('strength_range', ''),
                rr_profile=prediction.get('rr_profile', ''),
                market_conditions=prediction.get('market_conditions', ''),
                entry_price=entry_price,
                target_price=target_price,
                stop_loss=stop_loss,
                final_price=final_price,
                outcome=outcome_data.get('outcome', ''),
                max_drawdown=outcome_data.get('max_drawdown', 0.0),
                duration_minutes=outcome_data.get('duration_minutes', 0),
                success=success,
                rr_achieved=rr_achieved,
                risk_taken=risk_taken
            )
            
        except Exception as e:
            self.logger.error(f"Error converting prediction to outcome: {e}")
            return None
    
    async def _analyze_success_patterns(self, outcomes: List[PredictionOutcome], cluster_key: str) -> Optional[AnalysisResult]:
        """Analyze patterns in successful predictions"""
        try:
            successful = [o for o in outcomes if o.success]
            if len(successful) < 3:
                return None
            
            # Analyze common characteristics of successful predictions
            avg_duration = statistics.mean([o.duration_minutes for o in successful])
            avg_rr = statistics.mean([o.rr_achieved for o in successful])
            avg_drawdown = statistics.mean([o.max_drawdown for o in successful])
            
            recommendations = []
            if avg_duration < 60:
                recommendations.append("Successful predictions tend to complete quickly")
            if avg_rr > 2.0:
                recommendations.append("High R/R ratio is characteristic of success")
            if avg_drawdown < 0.05:
                recommendations.append("Low drawdown is associated with success")
            
            return AnalysisResult(
                analysis_type=AnalysisType.SUCCESS_PATTERN,
                cluster_key=cluster_key,
                sample_size=len(successful),
                success_rate=1.0,
                avg_rr=avg_rr,
                avg_duration=avg_duration,
                avg_drawdown=avg_drawdown,
                recommendations=recommendations,
                confidence=min(len(successful) / 10, 1.0),
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing success patterns: {e}")
            return None
    
    async def _analyze_rr_optimization(self, outcomes: List[PredictionOutcome], cluster_key: str) -> Optional[AnalysisResult]:
        """Analyze R/R optimization opportunities"""
        try:
            avg_rr = statistics.mean([o.rr_achieved for o in outcomes])
            success_rate = sum(1 for o in outcomes if o.success) / len(outcomes)
            
            recommendations = []
            if avg_rr < 1.5:
                recommendations.append("Consider increasing target prices")
            if success_rate < 0.5:
                recommendations.append("Consider tightening stop losses")
            if avg_rr > 3.0 and success_rate > 0.7:
                recommendations.append("Excellent R/R performance, consider scaling up")
            
            return AnalysisResult(
                analysis_type=AnalysisType.RR_OPTIMIZATION,
                cluster_key=cluster_key,
                sample_size=len(outcomes),
                success_rate=success_rate,
                avg_rr=avg_rr,
                avg_duration=statistics.mean([o.duration_minutes for o in outcomes]),
                avg_drawdown=statistics.mean([o.max_drawdown for o in outcomes]),
                recommendations=recommendations,
                confidence=min(len(outcomes) / 15, 1.0),
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing R/R optimization: {e}")
            return None
    
    async def _analyze_timing_optimization(self, outcomes: List[PredictionOutcome], cluster_key: str) -> Optional[AnalysisResult]:
        """Analyze timing optimization opportunities"""
        try:
            durations = [o.duration_minutes for o in outcomes]
            avg_duration = statistics.mean(durations)
            
            recommendations = []
            if avg_duration < 30:
                recommendations.append("Predictions complete very quickly, consider shorter timeframes")
            elif avg_duration > 240:
                recommendations.append("Predictions take long to complete, consider longer timeframes")
            
            return AnalysisResult(
                analysis_type=AnalysisType.TIMING_OPTIMIZATION,
                cluster_key=cluster_key,
                sample_size=len(outcomes),
                success_rate=sum(1 for o in outcomes if o.success) / len(outcomes),
                avg_rr=statistics.mean([o.rr_achieved for o in outcomes]),
                avg_duration=avg_duration,
                avg_drawdown=statistics.mean([o.max_drawdown for o in outcomes]),
                recommendations=recommendations,
                confidence=min(len(outcomes) / 12, 1.0),
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing timing optimization: {e}")
            return None
    
    async def _analyze_risk_optimization(self, outcomes: List[PredictionOutcome], cluster_key: str) -> Optional[AnalysisResult]:
        """Analyze risk optimization opportunities"""
        try:
            avg_drawdown = statistics.mean([o.max_drawdown for o in outcomes])
            max_drawdown = max([o.max_drawdown for o in outcomes])
            
            recommendations = []
            if avg_drawdown > 0.1:
                recommendations.append("High average drawdown, consider tighter stop losses")
            if max_drawdown > 0.2:
                recommendations.append("Very high maximum drawdown, review risk management")
            if avg_drawdown < 0.03:
                recommendations.append("Low drawdown, consider increasing position size")
            
            return AnalysisResult(
                analysis_type=AnalysisType.RISK_OPTIMIZATION,
                cluster_key=cluster_key,
                sample_size=len(outcomes),
                success_rate=sum(1 for o in outcomes if o.success) / len(outcomes),
                avg_rr=statistics.mean([o.rr_achieved for o in outcomes]),
                avg_duration=statistics.mean([o.duration_minutes for o in outcomes]),
                avg_drawdown=avg_drawdown,
                recommendations=recommendations,
                confidence=min(len(outcomes) / 10, 1.0),
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing risk optimization: {e}")
            return None
    
    def _calculate_evolution_priority(self, success_rate: float, avg_rr: float, sample_size: int) -> str:
        """Calculate evolution priority based on performance metrics"""
        if sample_size < 10:
            return "low"
        elif success_rate >= 0.8 and avg_rr >= 2.5:
            return "high"
        elif success_rate >= 0.6 and avg_rr >= 2.0:
            return "medium"
        elif success_rate < 0.4 or avg_rr < 1.0:
            return "urgent"
        else:
            return "low"


# Example usage and testing
if __name__ == "__main__":
    # Test the outcome analysis engine
    from src.utils.supabase_manager import SupabaseManager
    
    async def test_outcome_analysis():
        supabase_manager = SupabaseManager()
        engine = OutcomeAnalysisEngine(supabase_manager)
        
        # Test prediction data
        test_predictions = [
            {
                'id': 'pred_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'pattern_type': 'volume_spike',
                'strength_range': 'strong',
                'rr_profile': 'moderate',
                'market_conditions': 'moderate_volatility',
                'prediction_data': {
                    'entry_price': 50000.0,
                    'target_price': 52000.0,
                    'stop_loss': 48000.0
                },
                'outcome_data': {
                    'outcome': 'target_hit',
                    'final_price': 52100.0,
                    'max_drawdown': 0.02,
                    'duration_minutes': 45
                }
            }
        ]
        
        # Test analysis
        result = await engine.analyze_outcome_batch('test_cluster', test_predictions)
        print(f"Analysis result: {result}")
    
    import asyncio
    asyncio.run(test_outcome_analysis())
