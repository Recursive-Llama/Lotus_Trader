"""
CIL Integration - Strategic insights consumption and learning contribution

This component integrates with the Central Intelligence Layer (CIL) for strategic
insights consumption and learning contribution, enabling the Trader Team to
benefit from CIL's panoramic view and contribute execution insights back to the system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class CILIntegration:
    """Integrates with CIL for strategic insights and learning"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # CIL integration state
        self.consumed_insights = []
        self.contributed_insights = []
        self.resonance_scores = {}
        self.learning_contributions = []
        
        # Insight types we're interested in
        self.insight_types = [
            'execution_insights',
            'performance_analysis',
            'risk_insights',
            'venue_performance',
            'market_conditions',
            'strategy_insights'
        ]
        
        # Contribution types we provide
        self.contribution_types = [
            'execution_quality',
            'order_performance',
            'venue_insights',
            'execution_learning',
            'risk_observations'
        ]
        
    async def consume_cil_insights(self, execution_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Consume CIL insights relevant to execution
        
        Args:
            execution_context: Current execution context
            
        Returns:
            List of relevant CIL insights
        """
        try:
            symbol = execution_context.get('symbol', '')
            execution_type = execution_context.get('execution_type', '')
            
            # Query CIL meta-signals from AD_strands
            cil_insights = await self._query_cil_meta_signals(symbol, execution_type)
            
            # Filter and rank insights by relevance
            relevant_insights = await self._filter_relevant_insights(cil_insights, execution_context)
            
            # Apply insights to execution context
            applied_insights = await self._apply_insights_to_execution(relevant_insights, execution_context)
            
            # Store consumed insights
            for insight in applied_insights:
                self.consumed_insights.append({
                    'insight': insight,
                    'execution_context': execution_context,
                    'consumed_at': datetime.now()
                })
            
            # Publish insight consumption strand
            await self._publish_insight_consumption_strand(execution_context, applied_insights)
            
            logger.info(f"Consumed {len(applied_insights)} CIL insights for {symbol}")
            return applied_insights
            
        except Exception as e:
            logger.error(f"Error consuming CIL insights: {e}")
            return []
    
    async def contribute_execution_learning(self, execution_data: Dict[str, Any]) -> str:
        """
        Contribute execution learning to CIL
        
        Args:
            execution_data: Execution data to contribute
            
        Returns:
            Strand ID of the published learning contribution
        """
        try:
            # Generate execution learning insights
            learning_insights = await self._generate_execution_learning_insights(execution_data)
            
            # Create execution learning strand
            strand_id = await self._publish_execution_learning_strand(learning_insights)
            
            # Contribute to learning system
            await self._contribute_to_learning_system(learning_insights)
            
            # Store contribution
            self.learning_contributions.append({
                'learning_insights': learning_insights,
                'execution_data': execution_data,
                'contributed_at': datetime.now(),
                'strand_id': strand_id
            })
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error contributing execution learning: {e}")
            return ""
    
    async def participate_in_resonance(self, execution_pattern: Dict[str, Any]) -> float:
        """
        Participate in system resonance calculations
        
        Args:
            execution_pattern: Execution pattern data
            
        Returns:
            Resonance score for the execution pattern
        """
        try:
            # Calculate execution pattern resonance
            resonance_score = await self._calculate_execution_resonance(execution_pattern)
            
            # Contribute to global resonance field
            await self._contribute_to_global_resonance(execution_pattern, resonance_score)
            
            # Store resonance score
            pattern_id = execution_pattern.get('pattern_id', f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self.resonance_scores[pattern_id] = {
                'execution_pattern': execution_pattern,
                'resonance_score': resonance_score,
                'calculated_at': datetime.now()
            }
            
            # Publish resonance contribution strand
            await self._publish_resonance_contribution_strand(execution_pattern, resonance_score)
            
            logger.info(f"Calculated resonance score {resonance_score:.3f} for execution pattern")
            return resonance_score
            
        except Exception as e:
            logger.error(f"Error participating in resonance: {e}")
            return 0.0
    
    async def _query_cil_meta_signals(self, symbol: str, execution_type: str) -> List[Dict[str, Any]]:
        """Query CIL meta-signals from AD_strands"""
        try:
            # Query recent CIL meta-signals
            query = {
                'module': 'cil',
                'kind': 'meta_signal',
                'tags': ['cil:meta_signal', 'cil:strategic_insights']
            }
            
            if symbol:
                query['symbol'] = symbol
            
            # Get recent meta-signals (last 24 hours)
            since_time = datetime.now() - timedelta(hours=24)
            
            # This would typically use a more sophisticated query
            # For now, we'll simulate the query
            cil_insights = await self._simulate_cil_query(query, since_time)
            
            return cil_insights
            
        except Exception as e:
            logger.error(f"Error querying CIL meta-signals: {e}")
            return []
    
    async def _simulate_cil_query(self, query: Dict[str, Any], since_time: datetime) -> List[Dict[str, Any]]:
        """Simulate CIL query (placeholder for real implementation)"""
        # This would typically query the AD_strands table
        # For now, return mock CIL insights
        
        mock_insights = [
            {
                'id': 'cil_insight_001',
                'type': 'execution_insights',
                'symbol': query.get('symbol', 'BTC'),
                'content': {
                    'insight': 'High volume detected on BTC - consider reducing order size to minimize slippage',
                    'confidence': 0.85,
                    'source': 'volume_analysis',
                    'timestamp': datetime.now().isoformat()
                },
                'tags': ['cil:execution_insights', 'cil:volume_analysis'],
                'created_at': datetime.now().isoformat()
            },
            {
                'id': 'cil_insight_002',
                'type': 'venue_performance',
                'symbol': query.get('symbol', 'BTC'),
                'content': {
                    'insight': 'Hyperliquid showing 15% better execution quality than alternatives',
                    'confidence': 0.92,
                    'source': 'venue_comparison',
                    'timestamp': datetime.now().isoformat()
                },
                'tags': ['cil:venue_insights', 'cil:execution_quality'],
                'created_at': datetime.now().isoformat()
            },
            {
                'id': 'cil_insight_003',
                'type': 'risk_insights',
                'symbol': query.get('symbol', 'BTC'),
                'content': {
                    'insight': 'Market volatility increased - consider tighter stop losses',
                    'confidence': 0.78,
                    'source': 'volatility_analysis',
                    'timestamp': datetime.now().isoformat()
                },
                'tags': ['cil:risk_insights', 'cil:volatility_analysis'],
                'created_at': datetime.now().isoformat()
            }
        ]
        
        return mock_insights
    
    async def _filter_relevant_insights(self, cil_insights: List[Dict[str, Any]], execution_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter and rank insights by relevance to execution context"""
        try:
            relevant_insights = []
            
            for insight in cil_insights:
                relevance_score = await self._calculate_insight_relevance(insight, execution_context)
                
                if relevance_score > 0.5:  # Only include relevant insights
                    insight['relevance_score'] = relevance_score
                    relevant_insights.append(insight)
            
            # Sort by relevance score
            relevant_insights.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return relevant_insights
            
        except Exception as e:
            logger.error(f"Error filtering relevant insights: {e}")
            return []
    
    async def _calculate_insight_relevance(self, insight: Dict[str, Any], execution_context: Dict[str, Any]) -> float:
        """Calculate relevance score for an insight"""
        try:
            relevance_score = 0.0
            
            # Symbol match (40% weight)
            if insight.get('symbol') == execution_context.get('symbol'):
                relevance_score += 0.4
            
            # Type match (30% weight)
            insight_type = insight.get('type', '')
            if insight_type in self.insight_types:
                relevance_score += 0.3
            
            # Confidence score (20% weight)
            confidence = insight.get('content', {}).get('confidence', 0.5)
            relevance_score += confidence * 0.2
            
            # Recency (10% weight)
            created_at = insight.get('created_at', '')
            if created_at:
                try:
                    insight_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    time_diff = datetime.now() - insight_time
                    recency_score = max(0, 1 - time_diff.total_seconds() / 86400)  # 24 hours
                    relevance_score += recency_score * 0.1
                except:
                    relevance_score += 0.05  # Default recency score
            
            return min(1.0, max(0.0, relevance_score))
            
        except Exception as e:
            logger.error(f"Error calculating insight relevance: {e}")
            return 0.0
    
    async def _apply_insights_to_execution(self, insights: List[Dict[str, Any]], execution_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply insights to execution context"""
        try:
            applied_insights = []
            
            for insight in insights:
                # Apply insight to execution context
                applied_insight = await self._apply_single_insight(insight, execution_context)
                if applied_insight:
                    applied_insights.append(applied_insight)
            
            return applied_insights
            
        except Exception as e:
            logger.error(f"Error applying insights to execution: {e}")
            return []
    
    async def _apply_single_insight(self, insight: Dict[str, Any], execution_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply a single insight to execution context"""
        try:
            insight_type = insight.get('type', '')
            insight_content = insight.get('content', {})
            
            applied_insight = {
                'insight_id': insight.get('id', ''),
                'type': insight_type,
                'original_insight': insight,
                'applied_at': datetime.now().isoformat(),
                'execution_context': execution_context
            }
            
            # Apply insight based on type
            if insight_type == 'execution_insights':
                applied_insight['application'] = await self._apply_execution_insight(insight_content, execution_context)
            elif insight_type == 'venue_performance':
                applied_insight['application'] = await self._apply_venue_insight(insight_content, execution_context)
            elif insight_type == 'risk_insights':
                applied_insight['application'] = await self._apply_risk_insight(insight_content, execution_context)
            else:
                applied_insight['application'] = await self._apply_generic_insight(insight_content, execution_context)
            
            return applied_insight
            
        except Exception as e:
            logger.error(f"Error applying single insight: {e}")
            return None
    
    async def _apply_execution_insight(self, insight_content: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply execution insight to context"""
        insight_text = insight_content.get('insight', '')
        
        # Parse insight and apply to execution context
        if 'reduce order size' in insight_text.lower():
            return {
                'action': 'reduce_order_size',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
        elif 'increase order size' in insight_text.lower():
            return {
                'action': 'increase_order_size',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
        else:
            return {
                'action': 'consider_insight',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
    
    async def _apply_venue_insight(self, insight_content: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply venue insight to context"""
        insight_text = insight_content.get('insight', '')
        
        if 'hyperliquid' in insight_text.lower() and 'better' in insight_text.lower():
            return {
                'action': 'prefer_hyperliquid',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
        else:
            return {
                'action': 'consider_venue',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
    
    async def _apply_risk_insight(self, insight_content: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply risk insight to context"""
        insight_text = insight_content.get('insight', '')
        
        if 'tighter stop losses' in insight_text.lower():
            return {
                'action': 'tighten_stop_losses',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
        elif 'reduce position size' in insight_text.lower():
            return {
                'action': 'reduce_position_size',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
        else:
            return {
                'action': 'consider_risk',
                'reason': insight_text,
                'confidence': insight_content.get('confidence', 0.5)
            }
    
    async def _apply_generic_insight(self, insight_content: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply generic insight to context"""
        return {
            'action': 'consider_insight',
            'reason': insight_content.get('insight', ''),
            'confidence': insight_content.get('confidence', 0.5)
        }
    
    async def _generate_execution_learning_insights(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution learning insights from execution data"""
        try:
            # Extract key learning points
            learning_points = []
            
            # Execution quality insights
            if 'execution_quality' in execution_data:
                quality = execution_data['execution_quality']
                if quality.get('slippage', 0) > 0.01:  # 1% slippage
                    learning_points.append("High slippage detected - consider using limit orders")
                if quality.get('latency_ms', 0) > 1000:  # 1 second
                    learning_points.append("High latency detected - venue may be experiencing issues")
            
            # Performance insights
            if 'performance_analysis' in execution_data:
                performance = execution_data['performance_analysis']
                if performance.get('execution_score', 0) > 0.8:
                    learning_points.append("Excellent execution quality - strategy working well")
                elif performance.get('execution_score', 0) < 0.5:
                    learning_points.append("Poor execution quality - strategy needs improvement")
            
            # Venue insights
            if 'venue' in execution_data:
                venue = execution_data['venue']
                learning_points.append(f"Venue {venue} performance observed")
            
            # Create learning insights
            learning_insights = {
                'learning_type': 'execution_quality',
                'execution_data': execution_data,
                'learning_points': learning_points,
                'confidence_score': await self._calculate_learning_confidence(execution_data),
                'generated_at': datetime.now().isoformat()
            }
            
            return learning_insights
            
        except Exception as e:
            logger.error(f"Error generating execution learning insights: {e}")
            return {
                'learning_type': 'execution_quality',
                'execution_data': execution_data,
                'learning_points': [],
                'confidence_score': 0.0,
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    async def _calculate_learning_confidence(self, execution_data: Dict[str, Any]) -> float:
        """Calculate confidence score for learning insights"""
        try:
            confidence_factors = []
            
            # Data completeness factor
            if 'execution_quality' in execution_data:
                confidence_factors.append(0.8)
            if 'performance_analysis' in execution_data:
                confidence_factors.append(0.7)
            if 'venue' in execution_data:
                confidence_factors.append(0.6)
            
            # Data quality factor
            if 'execution_quality' in execution_data:
                execution_score = execution_data['execution_quality'].get('execution_score', 0)
                if execution_score > 0.7:
                    confidence_factors.append(0.9)
                else:
                    confidence_factors.append(0.5)
            
            # Return average confidence
            return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating learning confidence: {e}")
            return 0.5
    
    async def _calculate_execution_resonance(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate resonance score for execution pattern"""
        try:
            # Extract pattern characteristics
            pattern_type = execution_pattern.get('pattern_type', '')
            execution_score = execution_pattern.get('execution_score', 0)
            success_rate = execution_pattern.get('success_rate', 0)
            frequency = execution_pattern.get('frequency', 0)
            
            # Calculate φ (self-similarity) - how consistent is the pattern
            phi_score = await self._calculate_phi_score(execution_pattern)
            
            # Calculate ρ (feedback loops) - how consistent over time
            rho_score = await self._calculate_rho_score(execution_pattern)
            
            # Calculate θ (global field contribution) - how it contributes to global resonance
            theta_score = await self._calculate_theta_score(execution_pattern)
            
            # Combine scores
            resonance_score = (phi_score * 0.4 + rho_score * 0.3 + theta_score * 0.3)
            
            return min(1.0, max(0.0, resonance_score))
            
        except Exception as e:
            logger.error(f"Error calculating execution resonance: {e}")
            return 0.0
    
    async def _calculate_phi_score(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate φ (self-similarity) score"""
        # This would typically compare the pattern to similar patterns
        # For now, use execution score as a proxy
        return execution_pattern.get('execution_score', 0.5)
    
    async def _calculate_rho_score(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate ρ (feedback loops) score"""
        # This would typically analyze consistency over time
        # For now, use success rate as a proxy
        return execution_pattern.get('success_rate', 0.5)
    
    async def _calculate_theta_score(self, execution_pattern: Dict[str, Any]) -> float:
        """Calculate θ (global field) score"""
        # This would typically analyze contribution to global resonance
        # For now, use frequency as a proxy
        frequency = execution_pattern.get('frequency', 0)
        return min(1.0, frequency / 10.0)  # Normalize frequency
    
    async def _contribute_to_global_resonance(self, execution_pattern: Dict[str, Any], resonance_score: float):
        """Contribute to global resonance field"""
        try:
            # This would typically update the global resonance field
            # For now, just log the contribution
            logger.info(f"Contributing to global resonance: score={resonance_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error contributing to global resonance: {e}")
    
    async def _contribute_to_learning_system(self, learning_insights: Dict[str, Any]):
        """Contribute to the learning system"""
        try:
            # This would integrate with the strand-braid learning system
            # For now, just log the contribution
            logger.info(f"Contributing to learning system: {learning_insights.get('learning_type', '')}")
            
        except Exception as e:
            logger.error(f"Error contributing to learning system: {e}")
    
    async def _publish_insight_consumption_strand(self, execution_context: Dict[str, Any], applied_insights: List[Dict[str, Any]]):
        """Publish insight consumption strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'cil_insight_consumption',
                'symbol': execution_context.get('symbol', ''),
                'content': {
                    'execution_context': execution_context,
                    'applied_insights': applied_insights,
                    'insights_count': len(applied_insights),
                    'consumed_at': datetime.now().isoformat()
                },
                'tags': ['trader:cil_integration', 'trader:insight_consumption', 'cil:insight_usage']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published CIL insight consumption strand with {len(applied_insights)} insights")
            
        except Exception as e:
            logger.error(f"Error publishing insight consumption strand: {e}")
    
    async def _publish_execution_learning_strand(self, learning_insights: Dict[str, Any]) -> str:
        """Publish execution learning strand to AD_strands"""
        try:
            strand_id = f"execution_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            strand_data = {
                'id': strand_id,
                'module': 'trader',
                'kind': 'execution_learning',
                'content': {
                    'learning_type': learning_insights.get('learning_type', ''),
                    'learning_points': learning_insights.get('learning_points', []),
                    'confidence_score': learning_insights.get('confidence_score', 0),
                    'execution_data': learning_insights.get('execution_data', {}),
                    'generated_at': learning_insights.get('generated_at', '')
                },
                'tags': ['trader:execution_learning', 'trader:learning_contribution', 'cil:execution_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published execution learning strand: {strand_id}")
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error publishing execution learning strand: {e}")
            return ""
    
    async def _publish_resonance_contribution_strand(self, execution_pattern: Dict[str, Any], resonance_score: float):
        """Publish resonance contribution strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'resonance_contribution',
                'content': {
                    'execution_pattern': execution_pattern,
                    'resonance_score': resonance_score,
                    'contribution_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:resonance_contribution', 'trader:cil_integration', 'cil:resonance_field']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published resonance contribution strand: score={resonance_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error publishing resonance contribution strand: {e}")
    
    async def get_cil_integration_summary(self) -> Dict[str, Any]:
        """Get CIL integration summary"""
        try:
            return {
                'consumed_insights_count': len(self.consumed_insights),
                'contributed_insights_count': len(self.contributed_insights),
                'learning_contributions_count': len(self.learning_contributions),
                'resonance_scores_count': len(self.resonance_scores),
                'insight_types': self.insight_types,
                'contribution_types': self.contribution_types,
                'summary_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting CIL integration summary: {e}")
            return {
                'error': str(e),
                'summary_timestamp': datetime.now().isoformat()
            }
    
    async def get_recent_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent consumed insights"""
        return self.consumed_insights[-limit:] if limit > 0 else self.consumed_insights
    
    async def get_learning_contributions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent learning contributions"""
        return self.learning_contributions[-limit:] if limit > 0 else self.learning_contributions
    
    async def get_resonance_scores(self) -> Dict[str, Any]:
        """Get all resonance scores"""
        return self.resonance_scores
