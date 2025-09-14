"""
Position Tracker - Real-time position monitoring and risk management

This component tracks positions and manages risk in real-time, monitoring
position changes, P&L, and risk metrics while publishing updates through
strands for CIL and Decision Maker consumption.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class PositionTracker:
    """Tracks positions and manages risk in real-time"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.active_positions = {}  # Track active positions
        self.position_history = []  # Track position history
        self.risk_metrics = {}  # Track risk metrics
        
    async def track_position_updates(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track real-time position updates
        
        Args:
            position_data: Position data from order execution or market updates
            
        Returns:
            Dict with position tracking status
        """
        try:
            # Extract position information
            position_id = position_data.get('position_id', '')
            symbol = position_data.get('symbol', '')
            current_price = position_data.get('current_price', 0)
            quantity = position_data.get('quantity', 0)
            side = position_data.get('side', 'long')  # long or short
            
            if not position_id:
                return {
                    'status': 'error',
                    'message': 'Position ID is required'
                }
            
            # Update or create position
            if position_id in self.active_positions:
                await self._update_existing_position(position_id, position_data)
            else:
                await self._create_new_position(position_id, position_data)
            
            # Calculate position metrics
            position_metrics = await self._calculate_position_metrics(position_id, current_price)
            
            # Update risk metrics
            await self._update_risk_metrics(symbol, position_metrics)
            
            # Create position tracking result
            tracking_result = {
                'position_id': position_id,
                'symbol': symbol,
                'position_metrics': position_metrics,
                'risk_metrics': self.risk_metrics.get(symbol, {}),
                'tracking_timestamp': datetime.now().isoformat(),
                'status': 'tracking'
            }
            
            # Publish position tracking strand
            await self._publish_position_tracking_strand(tracking_result)
            
            return tracking_result
            
        except Exception as e:
            logger.error(f"Error tracking position updates: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def monitor_risk_metrics(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor risk metrics and exposure limits
        
        Args:
            position_data: Position data for risk analysis
            
        Returns:
            Dict with risk monitoring status
        """
        try:
            symbol = position_data.get('symbol', '')
            position_id = position_data.get('position_id', '')
            
            # Calculate position-specific risk metrics
            position_risk = await self._calculate_position_risk(position_data)
            
            # Calculate portfolio risk metrics
            portfolio_risk = await self._calculate_portfolio_risk()
            
            # Check risk limits
            risk_limits_check = await self._check_risk_limits(position_risk, portfolio_risk)
            
            # Generate risk alerts if needed
            risk_alerts = await self._generate_risk_alerts(risk_limits_check)
            
            # Create risk monitoring result
            risk_result = {
                'position_id': position_id,
                'symbol': symbol,
                'position_risk': position_risk,
                'portfolio_risk': portfolio_risk,
                'risk_limits_check': risk_limits_check,
                'risk_alerts': risk_alerts,
                'monitoring_timestamp': datetime.now().isoformat(),
                'status': 'monitoring'
            }
            
            # Publish risk monitoring strand
            await self._publish_risk_monitoring_strand(risk_result)
            
            return risk_result
            
        except Exception as e:
            logger.error(f"Error monitoring risk metrics: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def publish_position_strands(self, position_data: Dict[str, Any]) -> str:
        """
        Publish position updates through strands
        
        Args:
            position_data: Position data to publish
            
        Returns:
            Strand ID of the published position update
        """
        try:
            # Create position update strand
            strand_id = await self._publish_position_update_strand(position_data)
            
            # Create risk update strand if risk metrics are significant
            if position_data.get('risk_alerts'):
                await self._publish_risk_alert_strand(position_data)
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error publishing position strands: {e}")
            return ""
    
    async def _update_existing_position(self, position_id: str, position_data: Dict[str, Any]):
        """Update existing position with new data"""
        position = self.active_positions[position_id]
        
        # Update position data
        position['last_updated'] = datetime.now()
        position['current_price'] = position_data.get('current_price', position['current_price'])
        position['quantity'] = position_data.get('quantity', position['quantity'])
        position['unrealized_pnl'] = position_data.get('unrealized_pnl', position.get('unrealized_pnl', 0))
        position['realized_pnl'] = position_data.get('realized_pnl', position.get('realized_pnl', 0))
        
        # Update position history
        position['update_history'].append({
            'timestamp': datetime.now().isoformat(),
            'current_price': position['current_price'],
            'quantity': position['quantity'],
            'unrealized_pnl': position['unrealized_pnl']
        })
        
        logger.info(f"Updated position {position_id} with new data")
    
    async def _create_new_position(self, position_id: str, position_data: Dict[str, Any]):
        """Create new position"""
        position = {
            'position_id': position_id,
            'symbol': position_data.get('symbol', ''),
            'side': position_data.get('side', 'long'),
            'entry_price': position_data.get('entry_price', 0),
            'current_price': position_data.get('current_price', 0),
            'quantity': position_data.get('quantity', 0),
            'unrealized_pnl': 0,
            'realized_pnl': 0,
            'created_at': datetime.now(),
            'last_updated': datetime.now(),
            'update_history': [{
                'timestamp': datetime.now().isoformat(),
                'current_price': position_data.get('current_price', 0),
                'quantity': position_data.get('quantity', 0),
                'unrealized_pnl': 0
            }],
            'status': 'active'
        }
        
        self.active_positions[position_id] = position
        logger.info(f"Created new position {position_id}")
    
    async def _calculate_position_metrics(self, position_id: str, current_price: float) -> Dict[str, Any]:
        """Calculate position metrics"""
        if position_id not in self.active_positions:
            return {}
        
        position = self.active_positions[position_id]
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']
        
        # Calculate unrealized P&L
        if side == 'long':
            unrealized_pnl = (current_price - entry_price) * quantity
        else:  # short
            unrealized_pnl = (entry_price - current_price) * quantity
        
        # Calculate P&L percentage
        pnl_percentage = (unrealized_pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
        
        # Calculate position value
        position_value = current_price * quantity
        
        # Calculate time in position
        time_in_position = datetime.now() - position['created_at']
        
        # Update position with calculated metrics
        position['unrealized_pnl'] = unrealized_pnl
        position['pnl_percentage'] = pnl_percentage
        position['position_value'] = position_value
        position['time_in_position'] = time_in_position.total_seconds()
        
        return {
            'unrealized_pnl': unrealized_pnl,
            'pnl_percentage': pnl_percentage,
            'position_value': position_value,
            'time_in_position_seconds': time_in_position.total_seconds(),
            'entry_price': entry_price,
            'current_price': current_price,
            'quantity': quantity,
            'side': side
        }
    
    async def _update_risk_metrics(self, symbol: str, position_metrics: Dict[str, Any]):
        """Update risk metrics for symbol"""
        if symbol not in self.risk_metrics:
            self.risk_metrics[symbol] = {
                'total_exposure': 0,
                'total_pnl': 0,
                'position_count': 0,
                'last_updated': datetime.now()
            }
        
        risk_metrics = self.risk_metrics[symbol]
        risk_metrics['total_exposure'] += position_metrics.get('position_value', 0)
        risk_metrics['total_pnl'] += position_metrics.get('unrealized_pnl', 0)
        risk_metrics['position_count'] += 1
        risk_metrics['last_updated'] = datetime.now()
    
    async def _calculate_position_risk(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate position-specific risk metrics"""
        symbol = position_data.get('symbol', '')
        position_value = position_data.get('position_value', 0)
        unrealized_pnl = position_data.get('unrealized_pnl', 0)
        
        # Calculate position size as percentage of portfolio
        portfolio_value = await self._get_portfolio_value()
        position_size_percentage = (position_value / portfolio_value * 100) if portfolio_value > 0 else 0
        
        # Calculate VaR (Value at Risk) - simplified calculation
        var_95 = position_value * 0.05  # 5% VaR assumption
        var_99 = position_value * 0.01  # 1% VaR assumption
        
        # Calculate maximum drawdown potential
        max_drawdown_potential = position_value * 0.2  # 20% max drawdown assumption
        
        return {
            'position_size_percentage': position_size_percentage,
            'var_95': var_95,
            'var_99': var_99,
            'max_drawdown_potential': max_drawdown_potential,
            'unrealized_pnl': unrealized_pnl,
            'position_value': position_value
        }
    
    async def _calculate_portfolio_risk(self) -> Dict[str, Any]:
        """Calculate portfolio-wide risk metrics"""
        total_exposure = sum(risk['total_exposure'] for risk in self.risk_metrics.values())
        total_pnl = sum(risk['total_pnl'] for risk in self.risk_metrics.values())
        total_positions = sum(risk['position_count'] for risk in self.risk_metrics.values())
        
        # Calculate portfolio VaR
        portfolio_var_95 = total_exposure * 0.05
        portfolio_var_99 = total_exposure * 0.01
        
        # Calculate concentration risk
        concentration_risk = await self._calculate_concentration_risk()
        
        return {
            'total_exposure': total_exposure,
            'total_pnl': total_pnl,
            'total_positions': total_positions,
            'portfolio_var_95': portfolio_var_95,
            'portfolio_var_99': portfolio_var_99,
            'concentration_risk': concentration_risk
        }
    
    async def _calculate_concentration_risk(self) -> Dict[str, Any]:
        """Calculate concentration risk across positions"""
        if not self.risk_metrics:
            return {'max_concentration': 0, 'concentration_risk': 'low'}
        
        total_exposure = sum(risk['total_exposure'] for risk in self.risk_metrics.values())
        
        if total_exposure == 0:
            return {'max_concentration': 0, 'concentration_risk': 'low'}
        
        # Find maximum concentration
        max_concentration = 0
        for symbol, risk in self.risk_metrics.items():
            concentration = (risk['total_exposure'] / total_exposure) * 100
            max_concentration = max(max_concentration, concentration)
        
        # Categorize concentration risk
        if max_concentration > 50:
            concentration_risk = 'high'
        elif max_concentration > 25:
            concentration_risk = 'medium'
        else:
            concentration_risk = 'low'
        
        return {
            'max_concentration': max_concentration,
            'concentration_risk': concentration_risk,
            'symbol_concentrations': {
                symbol: (risk['total_exposure'] / total_exposure) * 100
                for symbol, risk in self.risk_metrics.items()
            }
        }
    
    async def _check_risk_limits(self, position_risk: Dict[str, Any], portfolio_risk: Dict[str, Any]) -> Dict[str, Any]:
        """Check risk limits and thresholds"""
        risk_limits = {
            'max_position_size': 20.0,  # 20% max position size
            'max_portfolio_var': 10.0,  # 10% max portfolio VaR
            'max_concentration': 30.0,  # 30% max concentration
            'max_drawdown': 15.0  # 15% max drawdown
        }
        
        limit_checks = {
            'position_size_ok': position_risk.get('position_size_percentage', 0) <= risk_limits['max_position_size'],
            'portfolio_var_ok': portfolio_risk.get('portfolio_var_95', 0) <= (portfolio_risk.get('total_exposure', 0) * risk_limits['max_portfolio_var'] / 100),
            'concentration_ok': portfolio_risk.get('concentration_risk', {}).get('max_concentration', 0) <= risk_limits['max_concentration'],
            'drawdown_ok': abs(portfolio_risk.get('total_pnl', 0)) <= (portfolio_risk.get('total_exposure', 0) * risk_limits['max_drawdown'] / 100)
        }
        
        # Overall risk status
        all_limits_ok = all(limit_checks.values())
        
        return {
            'risk_limits': risk_limits,
            'limit_checks': limit_checks,
            'all_limits_ok': all_limits_ok,
            'risk_status': 'within_limits' if all_limits_ok else 'exceeds_limits'
        }
    
    async def _generate_risk_alerts(self, risk_limits_check: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk alerts based on limit checks"""
        alerts = []
        
        if not risk_limits_check.get('all_limits_ok', True):
            limit_checks = risk_limits_check.get('limit_checks', {})
            
            if not limit_checks.get('position_size_ok', True):
                alerts.append({
                    'alert_type': 'position_size_limit',
                    'severity': 'high',
                    'message': 'Position size exceeds maximum allowed limit',
                    'recommendation': 'Consider reducing position size'
                })
            
            if not limit_checks.get('portfolio_var_ok', True):
                alerts.append({
                    'alert_type': 'portfolio_var_limit',
                    'severity': 'high',
                    'message': 'Portfolio VaR exceeds maximum allowed limit',
                    'recommendation': 'Consider reducing overall exposure'
                })
            
            if not limit_checks.get('concentration_ok', True):
                alerts.append({
                    'alert_type': 'concentration_limit',
                    'severity': 'medium',
                    'message': 'Position concentration exceeds maximum allowed limit',
                    'recommendation': 'Consider diversifying positions'
                })
            
            if not limit_checks.get('drawdown_ok', True):
                alerts.append({
                    'alert_type': 'drawdown_limit',
                    'severity': 'high',
                    'message': 'Portfolio drawdown exceeds maximum allowed limit',
                    'recommendation': 'Consider risk management actions'
                })
        
        return alerts
    
    async def _get_portfolio_value(self) -> float:
        """Get total portfolio value (placeholder for real implementation)"""
        # This would typically come from a portfolio management system
        # For now, return a mock portfolio value
        return 100000.0  # $100,000 mock portfolio value
    
    async def _publish_position_tracking_strand(self, tracking_result: Dict[str, Any]):
        """Publish position tracking strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'position_tracking',
                'symbol': tracking_result.get('symbol', ''),
                'content': {
                    'position_id': tracking_result.get('position_id', ''),
                    'position_metrics': tracking_result.get('position_metrics', {}),
                    'risk_metrics': tracking_result.get('risk_metrics', {}),
                    'tracking_timestamp': tracking_result.get('tracking_timestamp', '')
                },
                'tags': ['trader:position_tracking', 'trader:position_management']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published position tracking strand for {tracking_result.get('position_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing position tracking strand: {e}")
    
    async def _publish_risk_monitoring_strand(self, risk_result: Dict[str, Any]):
        """Publish risk monitoring strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'risk_monitoring',
                'symbol': risk_result.get('symbol', ''),
                'content': {
                    'position_id': risk_result.get('position_id', ''),
                    'position_risk': risk_result.get('position_risk', {}),
                    'portfolio_risk': risk_result.get('portfolio_risk', {}),
                    'risk_limits_check': risk_result.get('risk_limits_check', {}),
                    'risk_alerts': risk_result.get('risk_alerts', []),
                    'monitoring_timestamp': risk_result.get('monitoring_timestamp', '')
                },
                'tags': ['trader:risk_monitoring', 'trader:position_management', 'dm:risk_feedback']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published risk monitoring strand for {risk_result.get('position_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing risk monitoring strand: {e}")
    
    async def _publish_position_update_strand(self, position_data: Dict[str, Any]) -> str:
        """Publish position update strand to AD_strands"""
        try:
            strand_id = f"position_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            strand_data = {
                'id': strand_id,
                'module': 'trader',
                'kind': 'position_update',
                'symbol': position_data.get('symbol', ''),
                'content': {
                    'position_id': position_data.get('position_id', ''),
                    'position_data': position_data,
                    'update_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:position_update', 'trader:position_management']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published position update strand: {strand_id}")
            
            return strand_id
            
        except Exception as e:
            logger.error(f"Error publishing position update strand: {e}")
            return ""
    
    async def _publish_risk_alert_strand(self, position_data: Dict[str, Any]):
        """Publish risk alert strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'risk_alert',
                'symbol': position_data.get('symbol', ''),
                'content': {
                    'position_id': position_data.get('position_id', ''),
                    'risk_alerts': position_data.get('risk_alerts', []),
                    'alert_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:risk_alert', 'trader:position_management', 'dm:risk_feedback', 'cil:risk_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published risk alert strand for {position_data.get('position_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing risk alert strand: {e}")
    
    async def get_active_positions(self) -> Dict[str, Any]:
        """Get all active positions"""
        return {
            'active_positions': self.active_positions,
            'position_count': len(self.active_positions),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_position_history(self, position_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get position history"""
        history = self.position_history
        
        if position_id:
            history = [record for record in history if record.get('position_id') == position_id]
        
        return history[-limit:] if limit > 0 else history
    
    async def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk summary"""
        portfolio_risk = await self._calculate_portfolio_risk()
        risk_limits_check = await self._check_risk_limits({}, portfolio_risk)
        
        return {
            'portfolio_risk': portfolio_risk,
            'risk_limits_check': risk_limits_check,
            'active_positions': len(self.active_positions),
            'risk_metrics': self.risk_metrics,
            'summary_timestamp': datetime.now().isoformat()
        }
    
    async def close_position(self, position_id: str, close_price: float) -> Dict[str, Any]:
        """Close a position"""
        try:
            if position_id not in self.active_positions:
                return {
                    'status': 'error',
                    'message': f'Position {position_id} not found in active positions'
                }
            
            position = self.active_positions[position_id]
            
            # Calculate final P&L
            entry_price = position['entry_price']
            quantity = position['quantity']
            side = position['side']
            
            if side == 'long':
                realized_pnl = (close_price - entry_price) * quantity
            else:  # short
                realized_pnl = (entry_price - close_price) * quantity
            
            # Update position
            position['status'] = 'closed'
            position['close_price'] = close_price
            position['realized_pnl'] = realized_pnl
            position['closed_at'] = datetime.now()
            
            # Move to history
            self.position_history.append(position.copy())
            
            # Remove from active positions
            del self.active_positions[position_id]
            
            # Publish position closure strand
            await self._publish_position_closure_strand(position)
            
            return {
                'status': 'success',
                'position_id': position_id,
                'realized_pnl': realized_pnl,
                'closed_at': position['closed_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _publish_position_closure_strand(self, position: Dict[str, Any]):
        """Publish position closure strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'position_closure',
                'symbol': position.get('symbol', ''),
                'content': {
                    'position_id': position.get('position_id', ''),
                    'realized_pnl': position.get('realized_pnl', 0),
                    'close_price': position.get('close_price', 0),
                    'closed_at': position.get('closed_at', datetime.now()).isoformat(),
                    'position_summary': {
                        'entry_price': position.get('entry_price', 0),
                        'quantity': position.get('quantity', 0),
                        'side': position.get('side', ''),
                        'time_in_position': position.get('time_in_position', 0)
                    }
                },
                'tags': ['trader:position_closure', 'trader:position_management', 'trader:performance_analysis']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published position closure strand for {position.get('position_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing position closure strand: {e}")
