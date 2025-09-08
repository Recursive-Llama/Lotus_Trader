"""
Venue Fallback Manager - Fallback venue selection and performance tracking

This component manages venue fallback when primary venue fails, tracks venue
performance, and contributes to venue selection learning through strands.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import statistics

logger = logging.getLogger(__name__)


class VenueFallbackManager:
    """Manages venue fallback when primary venue fails"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Venue management
        self.available_venues = {
            'hyperliquid': {
                'name': 'Hyperliquid',
                'type': 'dex',
                'status': 'active',
                'priority': 1,
                'supported_assets': ['BTC', 'ETH', 'SOL', 'ARB', 'OP'],
                'min_order_size': 0.001,
                'max_order_size': 1000.0,
                'fees': {
                    'maker': 0.0002,  # 0.02%
                    'taker': 0.0005   # 0.05%
                }
            },
            'binance': {
                'name': 'Binance',
                'type': 'cex',
                'status': 'active',
                'priority': 2,
                'supported_assets': ['BTC', 'ETH', 'SOL', 'ADA', 'DOT'],
                'min_order_size': 0.001,
                'max_order_size': 10000.0,
                'fees': {
                    'maker': 0.001,   # 0.1%
                    'taker': 0.001    # 0.1%
                }
            },
            'coinbase': {
                'name': 'Coinbase Pro',
                'type': 'cex',
                'status': 'active',
                'priority': 3,
                'supported_assets': ['BTC', 'ETH', 'LTC', 'BCH'],
                'min_order_size': 0.001,
                'max_order_size': 5000.0,
                'fees': {
                    'maker': 0.005,   # 0.5%
                    'taker': 0.005    # 0.5%
                }
            }
        }
        
        # Performance tracking
        self.venue_performance = {}
        self.venue_fallback_history = []
        self.venue_availability = {}
        
        # Fallback logic
        self.fallback_rules = {
            'max_fallback_attempts': 3,
            'fallback_delay_seconds': 5,
            'performance_weight': 0.4,
            'availability_weight': 0.3,
            'fee_weight': 0.2,
            'priority_weight': 0.1
        }
        
    async def select_fallback_venue(self, order_data: Dict[str, Any]) -> str:
        """
        Select fallback venue when primary fails
        
        Args:
            order_data: Order data including symbol, quantity, etc.
            
        Returns:
            Selected fallback venue name
        """
        try:
            symbol = order_data.get('symbol', '')
            quantity = order_data.get('quantity', 0)
            primary_venue = order_data.get('venue', 'hyperliquid')
            
            # Get available venues for the symbol
            available_venues = await self._get_available_venues_for_symbol(symbol, quantity)
            
            if not available_venues:
                logger.error(f"No available venues for symbol {symbol}")
                return ""
            
            # Remove primary venue from available venues
            fallback_venues = [venue for venue in available_venues if venue != primary_venue]
            
            if not fallback_venues:
                logger.warning(f"No fallback venues available for {symbol}")
                return ""
            
            # Score venues based on performance and criteria
            venue_scores = await self._score_venues(fallback_venues, order_data)
            
            # Select best venue
            best_venue = max(venue_scores.items(), key=lambda x: x[1])[0]
            
            # Record fallback decision
            await self._record_fallback_decision(primary_venue, best_venue, order_data, venue_scores)
            
            # Publish fallback decision strand
            await self._publish_fallback_decision_strand(primary_venue, best_venue, order_data, venue_scores)
            
            logger.info(f"Selected fallback venue: {best_venue} for {symbol}")
            return best_venue
            
        except Exception as e:
            logger.error(f"Error selecting fallback venue: {e}")
            return ""
    
    async def track_venue_performance(self, venue: str, execution_result: Dict[str, Any]):
        """
        Track venue performance for future decisions
        
        Args:
            venue: Venue name
            execution_result: Execution result data
        """
        try:
            # Initialize venue performance tracking if not exists
            if venue not in self.venue_performance:
                self.venue_performance[venue] = {
                    'total_orders': 0,
                    'successful_orders': 0,
                    'failed_orders': 0,
                    'total_slippage': 0.0,
                    'total_latency': 0.0,
                    'total_fees': 0.0,
                    'average_slippage': 0.0,
                    'average_latency': 0.0,
                    'average_fees': 0.0,
                    'success_rate': 0.0,
                    'last_updated': datetime.now()
                }
            
            venue_perf = self.venue_performance[venue]
            
            # Update performance metrics
            venue_perf['total_orders'] += 1
            
            if execution_result.get('status') == 'success':
                venue_perf['successful_orders'] += 1
            else:
                venue_perf['failed_orders'] += 1
            
            # Update execution quality metrics
            if 'execution_quality' in execution_result:
                quality = execution_result['execution_quality']
                venue_perf['total_slippage'] += quality.get('slippage', 0)
                venue_perf['total_latency'] += quality.get('latency_ms', 0)
                venue_perf['total_fees'] += quality.get('fees', 0)
            
            # Calculate averages
            if venue_perf['total_orders'] > 0:
                venue_perf['average_slippage'] = venue_perf['total_slippage'] / venue_perf['total_orders']
                venue_perf['average_latency'] = venue_perf['total_latency'] / venue_perf['total_orders']
                venue_perf['average_fees'] = venue_perf['total_fees'] / venue_perf['total_orders']
                venue_perf['success_rate'] = venue_perf['successful_orders'] / venue_perf['total_orders']
            
            venue_perf['last_updated'] = datetime.now()
            
            # Publish venue performance strand
            await self._publish_venue_performance_strand(venue, venue_perf)
            
            logger.info(f"Updated venue performance for {venue}: success_rate={venue_perf['success_rate']:.2f}")
            
        except Exception as e:
            logger.error(f"Error tracking venue performance: {e}")
    
    async def get_venue_performance_summary(self, venue: Optional[str] = None) -> Dict[str, Any]:
        """
        Get venue performance summary
        
        Args:
            venue: Specific venue name, or None for all venues
            
        Returns:
            Dict with venue performance summary
        """
        try:
            if venue:
                if venue in self.venue_performance:
                    return {
                        'venue': venue,
                        'performance': self.venue_performance[venue],
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'venue': venue,
                        'performance': {},
                        'message': 'No performance data available',
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                return {
                    'all_venues': self.venue_performance,
                    'venue_count': len(self.venue_performance),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting venue performance summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def update_venue_availability(self, venue: str, is_available: bool, reason: str = ""):
        """
        Update venue availability status
        
        Args:
            venue: Venue name
            is_available: Whether venue is available
            reason: Reason for availability change
        """
        try:
            self.venue_availability[venue] = {
                'available': is_available,
                'reason': reason,
                'updated_at': datetime.now(),
                'status': 'active' if is_available else 'inactive'
            }
            
            # Update venue status in available_venues
            if venue in self.available_venues:
                self.available_venues[venue]['status'] = 'active' if is_available else 'inactive'
            
            # Publish venue availability strand
            await self._publish_venue_availability_strand(venue, is_available, reason)
            
            logger.info(f"Updated venue availability: {venue} = {is_available} ({reason})")
            
        except Exception as e:
            logger.error(f"Error updating venue availability: {e}")
    
    async def _get_available_venues_for_symbol(self, symbol: str, quantity: float) -> List[str]:
        """Get available venues for a specific symbol and quantity"""
        available_venues = []
        
        for venue_name, venue_info in self.available_venues.items():
            # Check if venue is active
            if venue_info['status'] != 'active':
                continue
            
            # Check if venue supports the symbol
            if symbol not in venue_info['supported_assets']:
                continue
            
            # Check if venue is available
            if venue_name in self.venue_availability:
                if not self.venue_availability[venue_name]['available']:
                    continue
            
            # Check quantity limits
            if quantity < venue_info['min_order_size'] or quantity > venue_info['max_order_size']:
                continue
            
            available_venues.append(venue_name)
        
        return available_venues
    
    async def _score_venues(self, venues: List[str], order_data: Dict[str, Any]) -> Dict[str, float]:
        """Score venues based on performance and criteria"""
        venue_scores = {}
        
        for venue in venues:
            score = 0.0
            
            # Performance score (40% weight)
            performance_score = await self._calculate_performance_score(venue)
            score += performance_score * self.fallback_rules['performance_weight']
            
            # Availability score (30% weight)
            availability_score = await self._calculate_availability_score(venue)
            score += availability_score * self.fallback_rules['availability_weight']
            
            # Fee score (20% weight)
            fee_score = await self._calculate_fee_score(venue, order_data)
            score += fee_score * self.fallback_rules['fee_weight']
            
            # Priority score (10% weight)
            priority_score = await self._calculate_priority_score(venue)
            score += priority_score * self.fallback_rules['priority_weight']
            
            venue_scores[venue] = score
        
        return venue_scores
    
    async def _calculate_performance_score(self, venue: str) -> float:
        """Calculate performance score for venue"""
        if venue not in self.venue_performance:
            return 0.5  # Default score for new venues
        
        perf = self.venue_performance[venue]
        
        # Base score on success rate
        success_rate = perf.get('success_rate', 0.5)
        
        # Adjust for execution quality
        avg_slippage = perf.get('average_slippage', 0.01)
        avg_latency = perf.get('average_latency', 1000)
        
        # Normalize scores (lower is better for slippage and latency)
        slippage_score = max(0, 1 - avg_slippage * 100)  # Convert to percentage
        latency_score = max(0, 1 - avg_latency / 1000)  # Normalize to seconds
        
        # Weighted performance score
        performance_score = (success_rate * 0.5 + slippage_score * 0.3 + latency_score * 0.2)
        
        return min(1.0, max(0.0, performance_score))
    
    async def _calculate_availability_score(self, venue: str) -> float:
        """Calculate availability score for venue"""
        if venue not in self.venue_availability:
            return 1.0  # Assume available if no data
        
        availability = self.venue_availability[venue]
        
        if availability['available']:
            return 1.0
        else:
            return 0.0
    
    async def _calculate_fee_score(self, venue: str, order_data: Dict[str, Any]) -> float:
        """Calculate fee score for venue"""
        if venue not in self.available_venues:
            return 0.5
        
        venue_info = self.available_venues[venue]
        fees = venue_info.get('fees', {})
        
        # Use taker fee for market orders, maker fee for limit orders
        order_type = order_data.get('order_type', 'limit')
        fee_rate = fees.get('taker' if order_type == 'market' else 'maker', 0.001)
        
        # Lower fees = higher score
        fee_score = max(0, 1 - fee_rate * 100)  # Convert to percentage
        
        return min(1.0, max(0.0, fee_score))
    
    async def _calculate_priority_score(self, venue: str) -> float:
        """Calculate priority score for venue"""
        if venue not in self.available_venues:
            return 0.5
        
        priority = self.available_venues[venue].get('priority', 5)
        
        # Lower priority number = higher score
        priority_score = max(0, 1 - (priority - 1) / 10)
        
        return min(1.0, max(0.0, priority_score))
    
    async def _record_fallback_decision(self, primary_venue: str, fallback_venue: str, order_data: Dict[str, Any], venue_scores: Dict[str, float]):
        """Record fallback decision for learning"""
        fallback_record = {
            'primary_venue': primary_venue,
            'fallback_venue': fallback_venue,
            'symbol': order_data.get('symbol', ''),
            'quantity': order_data.get('quantity', 0),
            'venue_scores': venue_scores,
            'decision_timestamp': datetime.now(),
            'reason': 'primary_venue_failed'
        }
        
        self.venue_fallback_history.append(fallback_record)
        
        # Keep only last 1000 records
        if len(self.venue_fallback_history) > 1000:
            self.venue_fallback_history = self.venue_fallback_history[-1000:]
    
    async def _publish_fallback_decision_strand(self, primary_venue: str, fallback_venue: str, order_data: Dict[str, Any], venue_scores: Dict[str, float]):
        """Publish fallback decision strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'venue_fallback_decision',
                'symbol': order_data.get('symbol', ''),
                'content': {
                    'primary_venue': primary_venue,
                    'fallback_venue': fallback_venue,
                    'order_data': order_data,
                    'venue_scores': venue_scores,
                    'decision_timestamp': datetime.now().isoformat(),
                    'reason': 'primary_venue_failed'
                },
                'tags': ['trader:venue_fallback', 'trader:venue_selection', 'trader:execution_quality']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published venue fallback decision strand: {primary_venue} -> {fallback_venue}")
            
        except Exception as e:
            logger.error(f"Error publishing fallback decision strand: {e}")
    
    async def _publish_venue_performance_strand(self, venue: str, performance: Dict[str, Any]):
        """Publish venue performance strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'venue_performance',
                'content': {
                    'venue': venue,
                    'performance': performance,
                    'performance_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:venue_performance', 'trader:execution_quality', 'cil:venue_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published venue performance strand for {venue}")
            
        except Exception as e:
            logger.error(f"Error publishing venue performance strand: {e}")
    
    async def _publish_venue_availability_strand(self, venue: str, is_available: bool, reason: str):
        """Publish venue availability strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'venue_availability',
                'content': {
                    'venue': venue,
                    'available': is_available,
                    'reason': reason,
                    'availability_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:venue_availability', 'trader:venue_selection']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published venue availability strand for {venue}: {is_available}")
            
        except Exception as e:
            logger.error(f"Error publishing venue availability strand: {e}")
    
    async def get_fallback_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get venue fallback history"""
        return self.venue_fallback_history[-limit:] if limit > 0 else self.venue_fallback_history
    
    async def get_venue_recommendations(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Get venue recommendations for a symbol and quantity"""
        try:
            # Get available venues
            available_venues = await self._get_available_venues_for_symbol(symbol, quantity)
            
            if not available_venues:
                return {
                    'recommendations': [],
                    'message': f'No available venues for {symbol}',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Score venues
            venue_scores = await self._score_venues(available_venues, {'symbol': symbol, 'quantity': quantity})
            
            # Sort by score
            sorted_venues = sorted(venue_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Create recommendations
            recommendations = []
            for venue, score in sorted_venues:
                venue_info = self.available_venues.get(venue, {})
                recommendation = {
                    'venue': venue,
                    'score': score,
                    'name': venue_info.get('name', venue),
                    'type': venue_info.get('type', 'unknown'),
                    'fees': venue_info.get('fees', {}),
                    'priority': venue_info.get('priority', 5)
                }
                recommendations.append(recommendation)
            
            return {
                'recommendations': recommendations,
                'symbol': symbol,
                'quantity': quantity,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting venue recommendations: {e}")
            return {
                'recommendations': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def analyze_venue_performance_trends(self) -> Dict[str, Any]:
        """Analyze venue performance trends"""
        try:
            trends = {}
            
            for venue, performance in self.venue_performance.items():
                # Calculate trend metrics
                total_orders = performance.get('total_orders', 0)
                success_rate = performance.get('success_rate', 0)
                avg_slippage = performance.get('average_slippage', 0)
                avg_latency = performance.get('average_latency', 0)
                
                # Categorize performance
                if success_rate >= 0.9:
                    performance_category = 'excellent'
                elif success_rate >= 0.8:
                    performance_category = 'good'
                elif success_rate >= 0.7:
                    performance_category = 'average'
                else:
                    performance_category = 'poor'
                
                trends[venue] = {
                    'performance_category': performance_category,
                    'total_orders': total_orders,
                    'success_rate': success_rate,
                    'average_slippage': avg_slippage,
                    'average_latency': avg_latency,
                    'last_updated': performance.get('last_updated', datetime.now())
                }
            
            return {
                'venue_trends': trends,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing venue performance trends: {e}")
            return {
                'venue_trends': {},
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    async def get_venue_summary(self) -> Dict[str, Any]:
        """Get comprehensive venue summary"""
        try:
            # Get performance trends
            trends = await self.analyze_venue_performance_trends()
            
            # Get availability status
            availability_status = {}
            for venue in self.available_venues.keys():
                if venue in self.venue_availability:
                    availability_status[venue] = self.venue_availability[venue]
                else:
                    availability_status[venue] = {
                        'available': True,
                        'status': 'active',
                        'reason': 'No data',
                        'updated_at': datetime.now()
                    }
            
            return {
                'available_venues': self.available_venues,
                'venue_performance': self.venue_performance,
                'venue_trends': trends.get('venue_trends', {}),
                'availability_status': availability_status,
                'fallback_history_count': len(self.venue_fallback_history),
                'summary_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting venue summary: {e}")
            return {
                'error': str(e),
                'summary_timestamp': datetime.now().isoformat()
            }
