"""
Performance Analyzer - Execution quality analysis and learning contribution

This component analyzes execution quality and contributes to system learning
by tracking execution metrics, comparing plan vs reality, and publishing
insights through strands for CIL consumption.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import statistics

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Analyzes execution quality and contributes to system learning"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.execution_history = []  # Track execution history
        self.performance_metrics = {}  # Track performance metrics
        
    async def analyze_execution_quality(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze execution quality metrics
        
        Args:
            execution_result: Result from order execution
            
        Returns:
            Dict with execution quality analysis
        """
        try:
            # Extract execution data
            order_id = execution_result.get('order_id', '')
            symbol = execution_result.get('symbol', '')
            order_details = execution_result.get('order_details', {})
            execution_time = execution_result.get('execution_time', 0)
            
            # Calculate execution quality metrics
            quality_metrics = await self._calculate_execution_metrics(execution_result)
            
            # Analyze venue performance
            venue_analysis = await self._analyze_venue_performance(execution_result)
            
            # Calculate overall execution score
            execution_score = await self._calculate_execution_score(quality_metrics, venue_analysis)
            
            # Store execution history
            execution_record = {
                'order_id': order_id,
                'symbol': symbol,
                'execution_time': datetime.now(),
                'quality_metrics': quality_metrics,
                'venue_analysis': venue_analysis,
                'execution_score': execution_score
            }
            self.execution_history.append(execution_record)
            
            # Update performance metrics
            await self._update_performance_metrics(symbol, quality_metrics, venue_analysis)
            
            # Create execution quality analysis
            analysis_result = {
                'order_id': order_id,
                'symbol': symbol,
                'execution_quality': quality_metrics,
                'venue_performance': venue_analysis,
                'execution_score': execution_score,
                'analysis_timestamp': datetime.now().isoformat(),
                'recommendations': await self._generate_execution_recommendations(quality_metrics, venue_analysis)
            }
            
            # Publish execution quality strand
            await self._publish_execution_quality_strand(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing execution quality: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'execution_score': 0.0
            }
    
    async def analyze_plan_vs_reality(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare trading plan expectations vs actual outcomes
        
        Args:
            position_data: Position data with plan and actual results
            
        Returns:
            Dict with plan vs reality analysis
        """
        try:
            # Extract plan and reality data
            original_plan = position_data.get('original_plan', {})
            actual_outcome = position_data.get('actual_outcome', {})
            position_id = position_data.get('position_id', '')
            
            if not original_plan or not actual_outcome:
                return {
                    'status': 'error',
                    'message': 'Missing original plan or actual outcome data'
                }
            
            # Compare expected vs actual outcomes
            comparison_analysis = await self._compare_expected_vs_actual(original_plan, actual_outcome)
            
            # Analyze timing differences
            timing_analysis = await self._analyze_timing_differences(original_plan, actual_outcome)
            
            # Analyze P&L differences
            pnl_analysis = await self._analyze_pnl_differences(original_plan, actual_outcome)
            
            # Generate insights
            insights = await self._generate_plan_vs_reality_insights(comparison_analysis, timing_analysis, pnl_analysis)
            
            # Create plan vs reality analysis
            analysis_result = {
                'position_id': position_id,
                'original_plan': original_plan,
                'actual_outcome': actual_outcome,
                'comparison_analysis': comparison_analysis,
                'timing_analysis': timing_analysis,
                'pnl_analysis': pnl_analysis,
                'insights': insights,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Publish plan vs reality strand
            await self._publish_plan_vs_reality_strand(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing plan vs reality: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def contribute_execution_insights(self, analysis_data: Dict[str, Any]) -> str:
        """
        Contribute execution insights to system learning
        
        Args:
            analysis_data: Analysis data to contribute
            
        Returns:
            Strand ID of the published insight
        """
        try:
            # Generate execution insights
            insights = await self._generate_execution_insights(analysis_data)
            
            # Create execution insight strand
            strand_id = await self._publish_execution_insight_strand(insights)
            
            # Contribute to learning system
            await self._contribute_to_learning_system(insights)
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error contributing execution insights: {e}")
            return ""
    
    async def _calculate_execution_metrics(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate execution quality metrics"""
        # Extract execution data
        order_details = execution_result.get('order_details', {})
        execution_time = execution_result.get('execution_time', 0)
        filled_price = execution_result.get('filled_price', 0)
        expected_price = execution_result.get('expected_price', 0)
        
        # Calculate slippage
        slippage = 0.0
        if expected_price > 0 and filled_price > 0:
            slippage = abs(filled_price - expected_price) / expected_price
        
        # Calculate latency (execution time in milliseconds)
        latency = execution_time * 1000 if execution_time > 0 else 0
        
        # Calculate fill rate
        filled_quantity = execution_result.get('filled_quantity', 0)
        requested_quantity = order_details.get('quantity', 0)
        fill_rate = filled_quantity / requested_quantity if requested_quantity > 0 else 0
        
        # Calculate execution efficiency score
        efficiency_score = await self._calculate_efficiency_score(slippage, latency, fill_rate)
        
        return {
            'slippage': slippage,
            'latency_ms': latency,
            'fill_rate': fill_rate,
            'efficiency_score': efficiency_score,
            'filled_price': filled_price,
            'expected_price': expected_price,
            'filled_quantity': filled_quantity,
            'requested_quantity': requested_quantity
        }
    
    async def _analyze_venue_performance(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze venue performance"""
        venue = execution_result.get('venue', 'unknown')
        
        # Get venue performance history
        venue_history = self.performance_metrics.get(venue, {})
        
        # Calculate venue-specific metrics
        venue_metrics = {
            'venue': venue,
            'execution_count': venue_history.get('execution_count', 0) + 1,
            'average_slippage': venue_history.get('average_slippage', 0.0),
            'average_latency': venue_history.get('average_latency', 0.0),
            'average_fill_rate': venue_history.get('average_fill_rate', 0.0),
            'success_rate': venue_history.get('success_rate', 0.0)
        }
        
        return venue_metrics
    
    async def _calculate_execution_score(self, quality_metrics: Dict[str, Any], venue_analysis: Dict[str, Any]) -> float:
        """Calculate overall execution score"""
        # Weight different factors
        slippage_weight = 0.3
        latency_weight = 0.2
        fill_rate_weight = 0.3
        venue_weight = 0.2
        
        # Normalize metrics (lower is better for slippage and latency)
        slippage_score = max(0, 1 - quality_metrics.get('slippage', 0) * 100)  # Convert to percentage
        latency_score = max(0, 1 - quality_metrics.get('latency_ms', 0) / 1000)  # Normalize to seconds
        fill_rate_score = quality_metrics.get('fill_rate', 0)
        venue_score = venue_analysis.get('success_rate', 0.5)
        
        # Calculate weighted score
        execution_score = (
            slippage_score * slippage_weight +
            latency_score * latency_weight +
            fill_rate_score * fill_rate_weight +
            venue_score * venue_weight
        )
        
        return min(1.0, max(0.0, execution_score))
    
    async def _generate_execution_recommendations(self, quality_metrics: Dict[str, Any], venue_analysis: Dict[str, Any]) -> List[str]:
        """Generate execution recommendations based on analysis"""
        recommendations = []
        
        # Slippage recommendations
        slippage = quality_metrics.get('slippage', 0)
        if slippage > 0.01:  # 1% slippage
            recommendations.append("Consider using limit orders to reduce slippage")
        elif slippage < 0.001:  # 0.1% slippage
            recommendations.append("Excellent slippage control - current strategy working well")
        
        # Latency recommendations
        latency = quality_metrics.get('latency_ms', 0)
        if latency > 1000:  # 1 second
            recommendations.append("High latency detected - consider venue optimization")
        elif latency < 100:  # 100ms
            recommendations.append("Excellent execution speed - venue performing well")
        
        # Fill rate recommendations
        fill_rate = quality_metrics.get('fill_rate', 0)
        if fill_rate < 0.8:  # 80% fill rate
            recommendations.append("Low fill rate - consider adjusting order size or timing")
        elif fill_rate >= 0.95:  # 95% fill rate
            recommendations.append("Excellent fill rate - order sizing appropriate")
        
        # Venue recommendations
        venue_success_rate = venue_analysis.get('success_rate', 0)
        if venue_success_rate < 0.7:  # 70% success rate
            recommendations.append("Consider alternative venue - current venue underperforming")
        elif venue_success_rate >= 0.9:  # 90% success rate
            recommendations.append("Venue performing excellently - continue current strategy")
        
        return recommendations
    
    async def _compare_expected_vs_actual(self, original_plan: Dict[str, Any], actual_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Compare expected vs actual outcomes"""
        expected_pnl = original_plan.get('expected_pnl', 0)
        actual_pnl = actual_outcome.get('actual_pnl', 0)
        
        expected_duration = original_plan.get('expected_duration', 0)
        actual_duration = actual_outcome.get('actual_duration', 0)
        
        expected_entry_price = original_plan.get('expected_entry_price', 0)
        actual_entry_price = actual_outcome.get('actual_entry_price', 0)
        
        expected_exit_price = original_plan.get('expected_exit_price', 0)
        actual_exit_price = actual_outcome.get('actual_exit_price', 0)
        
        return {
            'pnl_difference': actual_pnl - expected_pnl,
            'pnl_percentage_diff': ((actual_pnl - expected_pnl) / expected_pnl * 100) if expected_pnl != 0 else 0,
            'duration_difference': actual_duration - expected_duration,
            'duration_percentage_diff': ((actual_duration - expected_duration) / expected_duration * 100) if expected_duration != 0 else 0,
            'entry_price_difference': actual_entry_price - expected_entry_price,
            'exit_price_difference': actual_exit_price - expected_exit_price,
            'expected_pnl': expected_pnl,
            'actual_pnl': actual_pnl,
            'expected_duration': expected_duration,
            'actual_duration': actual_duration
        }
    
    async def _analyze_timing_differences(self, original_plan: Dict[str, Any], actual_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze timing differences between plan and reality"""
        expected_entry_time = original_plan.get('expected_entry_time', '')
        actual_entry_time = actual_outcome.get('actual_entry_time', '')
        
        expected_exit_time = original_plan.get('expected_exit_time', '')
        actual_exit_time = actual_outcome.get('actual_exit_time', '')
        
        # Parse timestamps and calculate differences
        entry_time_diff = 0
        exit_time_diff = 0
        
        if expected_entry_time and actual_entry_time:
            expected_entry_dt = datetime.fromisoformat(expected_entry_time)
            actual_entry_dt = datetime.fromisoformat(actual_entry_time)
            entry_time_diff = (actual_entry_dt - expected_entry_dt).total_seconds()
        
        if expected_exit_time and actual_exit_time:
            expected_exit_dt = datetime.fromisoformat(expected_exit_time)
            actual_exit_dt = datetime.fromisoformat(actual_exit_time)
            exit_time_diff = (actual_exit_dt - expected_exit_dt).total_seconds()
        
        return {
            'entry_time_difference_seconds': entry_time_diff,
            'exit_time_difference_seconds': exit_time_diff,
            'entry_timing_accuracy': 'early' if entry_time_diff < 0 else 'late' if entry_time_diff > 0 else 'on_time',
            'exit_timing_accuracy': 'early' if exit_time_diff < 0 else 'late' if exit_time_diff > 0 else 'on_time',
            'expected_entry_time': expected_entry_time,
            'actual_entry_time': actual_entry_time,
            'expected_exit_time': expected_exit_time,
            'actual_exit_time': actual_exit_time
        }
    
    async def _analyze_pnl_differences(self, original_plan: Dict[str, Any], actual_outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze P&L differences between plan and reality"""
        expected_pnl = original_plan.get('expected_pnl', 0)
        actual_pnl = actual_outcome.get('actual_pnl', 0)
        
        expected_pnl_percentage = original_plan.get('expected_pnl_percentage', 0)
        actual_pnl_percentage = actual_outcome.get('actual_pnl_percentage', 0)
        
        pnl_difference = actual_pnl - expected_pnl
        pnl_percentage_diff = actual_pnl_percentage - expected_pnl_percentage
        
        # Categorize performance
        performance_category = 'meets_expectations'
        if pnl_difference > expected_pnl * 0.1:  # 10% better than expected
            performance_category = 'exceeds_expectations'
        elif pnl_difference < -expected_pnl * 0.1:  # 10% worse than expected
            performance_category = 'below_expectations'
        
        return {
            'pnl_difference': pnl_difference,
            'pnl_percentage_difference': pnl_percentage_diff,
            'performance_category': performance_category,
            'expected_pnl': expected_pnl,
            'actual_pnl': actual_pnl,
            'expected_pnl_percentage': expected_pnl_percentage,
            'actual_pnl_percentage': actual_pnl_percentage
        }
    
    async def _generate_plan_vs_reality_insights(self, comparison_analysis: Dict[str, Any], timing_analysis: Dict[str, Any], pnl_analysis: Dict[str, Any]) -> List[str]:
        """Generate insights from plan vs reality analysis"""
        insights = []
        
        # P&L insights
        pnl_diff = pnl_analysis.get('pnl_difference', 0)
        if pnl_diff > 0:
            insights.append(f"Position exceeded expectations by {pnl_diff:.2f} - strategy performed better than anticipated")
        elif pnl_diff < 0:
            insights.append(f"Position underperformed by {abs(pnl_diff):.2f} - consider adjusting strategy parameters")
        else:
            insights.append("Position met expectations exactly - strategy working as planned")
        
        # Timing insights
        entry_timing = timing_analysis.get('entry_timing_accuracy', 'on_time')
        exit_timing = timing_analysis.get('exit_timing_accuracy', 'on_time')
        
        if entry_timing == 'early':
            insights.append("Entry was earlier than expected - market conditions may have been more favorable")
        elif entry_timing == 'late':
            insights.append("Entry was later than expected - may have missed optimal entry point")
        
        if exit_timing == 'early':
            insights.append("Exit was earlier than expected - may have left profit on the table")
        elif exit_timing == 'late':
            insights.append("Exit was later than expected - may have held position too long")
        
        # Performance category insights
        performance_category = pnl_analysis.get('performance_category', 'meets_expectations')
        if performance_category == 'exceeds_expectations':
            insights.append("Strategy exceeded expectations - consider scaling up similar positions")
        elif performance_category == 'below_expectations':
            insights.append("Strategy underperformed - review and adjust parameters before next execution")
        
        return insights
    
    async def _generate_execution_insights(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution insights from analysis data"""
        insights = {
            'insight_type': 'execution_quality',
            'analysis_timestamp': datetime.now().isoformat(),
            'key_findings': [],
            'recommendations': [],
            'lessons_learned': [],
            'confidence_score': 0.0
        }
        
        # Extract key findings
        if 'execution_quality' in analysis_data:
            quality_metrics = analysis_data['execution_quality']
            insights['key_findings'].append(f"Execution score: {quality_metrics.get('execution_score', 0):.2f}")
            insights['key_findings'].append(f"Slippage: {quality_metrics.get('slippage', 0):.4f}")
            insights['key_findings'].append(f"Latency: {quality_metrics.get('latency_ms', 0):.0f}ms")
        
        # Extract recommendations
        if 'recommendations' in analysis_data:
            insights['recommendations'] = analysis_data['recommendations']
        
        # Generate lessons learned
        insights['lessons_learned'] = await self._generate_lessons_learned(analysis_data)
        
        # Calculate confidence score
        insights['confidence_score'] = await self._calculate_insight_confidence(analysis_data)
        
        return insights
    
    async def _generate_lessons_learned(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Generate lessons learned from analysis data"""
        lessons = []
        
        # Execution quality lessons
        if 'execution_quality' in analysis_data:
            quality_metrics = analysis_data['execution_quality']
            execution_score = quality_metrics.get('execution_score', 0)
            
            if execution_score > 0.8:
                lessons.append("High execution quality achieved - current execution strategy is effective")
            elif execution_score < 0.5:
                lessons.append("Low execution quality - execution strategy needs improvement")
        
        # Plan vs reality lessons
        if 'plan_vs_reality' in analysis_data:
            pnl_analysis = analysis_data['plan_vs_reality'].get('pnl_analysis', {})
            performance_category = pnl_analysis.get('performance_category', 'meets_expectations')
            
            if performance_category == 'exceeds_expectations':
                lessons.append("Strategy exceeded expectations - consider increasing position size for similar setups")
            elif performance_category == 'below_expectations':
                lessons.append("Strategy underperformed - review entry/exit criteria and risk management")
        
        return lessons
    
    async def _calculate_insight_confidence(self, analysis_data: Dict[str, Any]) -> float:
        """Calculate confidence score for insights"""
        confidence_factors = []
        
        # Data completeness factor
        if 'execution_quality' in analysis_data and 'plan_vs_reality' in analysis_data:
            confidence_factors.append(0.9)  # High confidence with both analyses
        elif 'execution_quality' in analysis_data or 'plan_vs_reality' in analysis_data:
            confidence_factors.append(0.6)  # Medium confidence with one analysis
        else:
            confidence_factors.append(0.3)  # Low confidence with limited data
        
        # Data quality factor
        if 'execution_quality' in analysis_data:
            execution_score = analysis_data['execution_quality'].get('execution_score', 0)
            if execution_score > 0.7:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.5)
        
        # Return average confidence
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    async def _update_performance_metrics(self, symbol: str, quality_metrics: Dict[str, Any], venue_analysis: Dict[str, Any]):
        """Update performance metrics"""
        venue = venue_analysis.get('venue', 'unknown')
        
        if venue not in self.performance_metrics:
            self.performance_metrics[venue] = {
                'execution_count': 0,
                'total_slippage': 0.0,
                'total_latency': 0.0,
                'total_fill_rate': 0.0,
                'successful_executions': 0
            }
        
        venue_metrics = self.performance_metrics[venue]
        venue_metrics['execution_count'] += 1
        venue_metrics['total_slippage'] += quality_metrics.get('slippage', 0)
        venue_metrics['total_latency'] += quality_metrics.get('latency_ms', 0)
        venue_metrics['total_fill_rate'] += quality_metrics.get('fill_rate', 0)
        
        if quality_metrics.get('execution_score', 0) > 0.7:
            venue_metrics['successful_executions'] += 1
        
        # Calculate averages
        venue_metrics['average_slippage'] = venue_metrics['total_slippage'] / venue_metrics['execution_count']
        venue_metrics['average_latency'] = venue_metrics['total_latency'] / venue_metrics['execution_count']
        venue_metrics['average_fill_rate'] = venue_metrics['total_fill_rate'] / venue_metrics['execution_count']
        venue_metrics['success_rate'] = venue_metrics['successful_executions'] / venue_metrics['execution_count']
    
    async def _calculate_efficiency_score(self, slippage: float, latency: float, fill_rate: float) -> float:
        """Calculate execution efficiency score"""
        # Normalize metrics (lower is better for slippage and latency)
        slippage_score = max(0, 1 - slippage * 100)  # Convert to percentage
        latency_score = max(0, 1 - latency / 1000)  # Normalize to seconds
        fill_rate_score = fill_rate
        
        # Weighted average
        efficiency_score = (slippage_score * 0.4 + latency_score * 0.3 + fill_rate_score * 0.3)
        return min(1.0, max(0.0, efficiency_score))
    
    async def _publish_execution_quality_strand(self, analysis_result: Dict[str, Any]):
        """Publish execution quality strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'execution_quality',
                'symbol': analysis_result.get('symbol', ''),
                'content': {
                    'order_id': analysis_result.get('order_id', ''),
                    'execution_quality': analysis_result.get('execution_quality', {}),
                    'venue_performance': analysis_result.get('venue_performance', {}),
                    'execution_score': analysis_result.get('execution_score', 0),
                    'recommendations': analysis_result.get('recommendations', []),
                    'analysis_timestamp': analysis_result.get('analysis_timestamp', '')
                },
                'tags': ['trader:execution_quality', 'trader:performance_analysis']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published execution quality strand for {analysis_result.get('order_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing execution quality strand: {e}")
    
    async def _publish_plan_vs_reality_strand(self, analysis_result: Dict[str, Any]):
        """Publish plan vs reality strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'plan_vs_reality',
                'content': {
                    'position_id': analysis_result.get('position_id', ''),
                    'comparison_analysis': analysis_result.get('comparison_analysis', {}),
                    'timing_analysis': analysis_result.get('timing_analysis', {}),
                    'pnl_analysis': analysis_result.get('pnl_analysis', {}),
                    'insights': analysis_result.get('insights', []),
                    'analysis_timestamp': analysis_result.get('analysis_timestamp', '')
                },
                'tags': ['trader:plan_vs_reality', 'trader:performance_analysis', 'cil:execution_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published plan vs reality strand for {analysis_result.get('position_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing plan vs reality strand: {e}")
    
    async def _publish_execution_insight_strand(self, insights: Dict[str, Any]) -> str:
        """Publish execution insight strand to AD_strands"""
        try:
            strand_id = f"execution_insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            strand_data = {
                'id': strand_id,
                'module': 'trader',
                'kind': 'execution_insights',
                'content': {
                    'insight_type': insights.get('insight_type', ''),
                    'key_findings': insights.get('key_findings', []),
                    'recommendations': insights.get('recommendations', []),
                    'lessons_learned': insights.get('lessons_learned', []),
                    'confidence_score': insights.get('confidence_score', 0),
                    'analysis_timestamp': insights.get('analysis_timestamp', '')
                },
                'tags': ['trader:execution_insights', 'cil:execution_insights', 'trader:learning_contribution']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published execution insight strand: {strand_id}")
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error publishing execution insight strand: {e}")
            return ""
    
    async def _contribute_to_learning_system(self, insights: Dict[str, Any]):
        """Contribute insights to the learning system"""
        try:
            # This will integrate with the strand-braid learning system
            # For now, just log the contribution
            logger.info(f"Contributing execution insights to learning system: {insights.get('insight_type', '')}")
            
            # Future: Integrate with CIL learning system
            # await self.cil_integration.contribute_execution_learning(insights)
            
        except Exception as e:
            logger.error(f"Error contributing to learning system: {e}")
    
    async def get_execution_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history"""
        history = self.execution_history
        
        if symbol:
            history = [record for record in history if record.get('symbol') == symbol]
        
        return history[-limit:] if limit > 0 else history
    
    async def get_performance_metrics(self, venue: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        if venue:
            return self.performance_metrics.get(venue, {})
        else:
            return self.performance_metrics
    
    async def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        total_executions = len(self.execution_history)
        
        if total_executions == 0:
            return {
                'total_executions': 0,
                'average_execution_score': 0.0,
                'total_venues': 0,
                'summary_timestamp': datetime.now().isoformat()
            }
        
        # Calculate average execution score
        execution_scores = [record.get('execution_score', 0) for record in self.execution_history]
        average_execution_score = sum(execution_scores) / len(execution_scores)
        
        # Count venues
        venues = set()
        for record in self.execution_history:
            venue_analysis = record.get('venue_analysis', {})
            venue = venue_analysis.get('venue', 'unknown')
            venues.add(venue)
        
        return {
            'total_executions': total_executions,
            'average_execution_score': average_execution_score,
            'total_venues': len(venues),
            'venues': list(venues),
            'summary_timestamp': datetime.now().isoformat()
        }
