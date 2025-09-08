"""
Portfolio Data Integration for Decision Maker

This module handles Decision Maker's integration with external portfolio data sources,
primarily Hyperliquid API/WebSocket for real-time portfolio state, position tracking,
and risk assessment data.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
import aiohttp
import websockets
from dataclasses import dataclass

@dataclass
class Position:
    """Portfolio position data"""
    symbol: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin_used: float
    leverage: float
    side: str  # 'long' or 'short'

@dataclass
class PortfolioState:
    """Complete portfolio state"""
    total_value: float
    available_margin: float
    used_margin: float
    total_pnl: float
    positions: List[Position]
    last_updated: datetime
    risk_metrics: Dict[str, Any]

class PortfolioDataIntegration:
    """
    Handles Decision Maker's integration with external portfolio data sources.
    
    This provides real-time portfolio state for risk assessment and decision making.
    Uses hybrid API/WebSocket approach for reliable and efficient data access.
    """

    def __init__(self, supabase_manager: Any, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.supabase_manager = supabase_manager
        self.config = config or {}
        
        # Hyperliquid configuration
        self.hyperliquid_api_url = self.config.get('hyperliquid_api_url', 'https://api.hyperliquid.xyz')
        self.hyperliquid_ws_url = self.config.get('hyperliquid_ws_url', 'wss://api.hyperliquid.xyz/ws')
        self.api_key = self.config.get('api_key', '')
        self.secret_key = self.config.get('secret_key', '')
        
        # Portfolio state
        self.current_portfolio_state: Optional[PortfolioState] = None
        self.portfolio_history: List[PortfolioState] = []
        
        # WebSocket connection
        self.websocket_connection = None
        self.websocket_task = None
        self.websocket_connected = False
        
        # API session
        self.api_session = None
        
        # Callbacks for portfolio updates
        self.portfolio_update_callbacks: List[Callable] = []
        self.risk_alert_callbacks: List[Callable] = []
        
        # Risk thresholds
        self.risk_thresholds = {
            'max_drawdown': 0.05,  # 5% max drawdown
            'max_position_size': 0.1,  # 10% max position
            'max_leverage': 3.0,  # 3x max leverage
            'min_margin_ratio': 0.2  # 20% min margin ratio
        }
    
    async def initialize(self):
        """Initialize portfolio data integration."""
        try:
            self.logger.info("Initializing portfolio data integration...")
            
            # Initialize API session
            self.api_session = aiohttp.ClientSession()
            
            # Get initial portfolio state
            await self._get_initial_portfolio_state()
            
            # Start WebSocket connection
            await self._start_websocket_connection()
            
            self.logger.info("Portfolio data integration initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize portfolio data integration: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown portfolio data integration."""
        try:
            self.logger.info("Shutting down portfolio data integration...")
            
            # Stop WebSocket connection
            if self.websocket_task:
                self.websocket_task.cancel()
                try:
                    await self.websocket_task
                except asyncio.CancelledError:
                    pass
            
            if self.websocket_connection:
                await self.websocket_connection.close()
            
            # Close API session
            if self.api_session:
                await self.api_session.close()
            
            self.logger.info("Portfolio data integration shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error shutting down portfolio data integration: {e}")
    
    async def _get_initial_portfolio_state(self):
        """Get initial portfolio state via API."""
        try:
            self.logger.info("Getting initial portfolio state...")
            
            # Get user state from Hyperliquid API
            user_state = await self._api_get_user_state()
            
            # Get positions
            positions = await self._api_get_positions()
            
            # Calculate portfolio metrics
            portfolio_state = await self._calculate_portfolio_state(user_state, positions)
            
            # Store current state
            self.current_portfolio_state = portfolio_state
            self.portfolio_history.append(portfolio_state)
            
            self.logger.info(f"Initial portfolio state loaded: {portfolio_state.total_value:.2f} total value")
            
        except Exception as e:
            self.logger.error(f"Error getting initial portfolio state: {e}")
    
    async def _start_websocket_connection(self):
        """Start WebSocket connection for real-time updates."""
        try:
            self.logger.info("Starting WebSocket connection...")
            
            # Create WebSocket connection
            self.websocket_connection = await websockets.connect(self.hyperliquid_ws_url)
            self.websocket_connected = True
            
            # Start WebSocket task
            self.websocket_task = asyncio.create_task(self._websocket_listener())
            
            self.logger.info("WebSocket connection started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket connection: {e}")
            self.websocket_connected = False
    
    async def _websocket_listener(self):
        """Listen for WebSocket messages."""
        try:
            while self.websocket_connected:
                try:
                    # Receive message
                    message = await self.websocket_connection.recv()
                    data = json.loads(message)
                    
                    # Process message
                    await self._process_websocket_message(data)
                    
                except websockets.exceptions.ConnectionClosed:
                    self.logger.warning("WebSocket connection closed, attempting to reconnect...")
                    await self._reconnect_websocket()
                    break
                    
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            self.logger.info("WebSocket listener cancelled")
        except Exception as e:
            self.logger.error(f"Error in WebSocket listener: {e}")
    
    async def _process_websocket_message(self, data: Dict[str, Any]):
        """Process WebSocket message."""
        try:
            message_type = data.get('type', '')
            
            if message_type == 'position_update':
                await self._handle_position_update(data)
            elif message_type == 'portfolio_update':
                await self._handle_portfolio_update(data)
            elif message_type == 'risk_alert':
                await self._handle_risk_alert(data)
            else:
                self.logger.debug(f"Unknown WebSocket message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing WebSocket message: {e}")
    
    async def _handle_position_update(self, data: Dict[str, Any]):
        """Handle position update from WebSocket."""
        try:
            # Update current portfolio state
            if self.current_portfolio_state:
                await self._update_portfolio_state_from_websocket(data)
                
                # Check for risk alerts
                await self._check_risk_alerts()
                
                # Notify callbacks
                await self._notify_portfolio_update_callbacks()
            
        except Exception as e:
            self.logger.error(f"Error handling position update: {e}")
    
    async def _handle_portfolio_update(self, data: Dict[str, Any]):
        """Handle portfolio update from WebSocket."""
        try:
            # Update current portfolio state
            if self.current_portfolio_state:
                await self._update_portfolio_state_from_websocket(data)
                
                # Check for risk alerts
                await self._check_risk_alerts()
                
                # Notify callbacks
                await self._notify_portfolio_update_callbacks()
            
        except Exception as e:
            self.logger.error(f"Error handling portfolio update: {e}")
    
    async def _handle_risk_alert(self, data: Dict[str, Any]):
        """Handle risk alert from WebSocket."""
        try:
            self.logger.warning(f"Risk alert received: {data}")
            
            # Notify risk alert callbacks
            await self._notify_risk_alert_callbacks(data)
            
        except Exception as e:
            self.logger.error(f"Error handling risk alert: {e}")
    
    async def _reconnect_websocket(self):
        """Reconnect WebSocket connection."""
        try:
            self.logger.info("Attempting to reconnect WebSocket...")
            
            # Close existing connection
            if self.websocket_connection:
                await self.websocket_connection.close()
            
            # Wait before reconnecting
            await asyncio.sleep(5)
            
            # Reconnect
            await self._start_websocket_connection()
            
        except Exception as e:
            self.logger.error(f"Error reconnecting WebSocket: {e}")
    
    async def _api_get_user_state(self) -> Dict[str, Any]:
        """Get user state from Hyperliquid API."""
        try:
            # This would be the actual API call to Hyperliquid
            # For now, we'll simulate the response
            return {
                'total_value': 100000.0,
                'available_margin': 50000.0,
                'used_margin': 50000.0,
                'total_pnl': 1000.0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user state from API: {e}")
            return {}
    
    async def _api_get_positions(self) -> List[Dict[str, Any]]:
        """Get positions from Hyperliquid API."""
        try:
            # This would be the actual API call to Hyperliquid
            # For now, we'll simulate the response
            return [
                {
                    'symbol': 'BTC',
                    'size': 0.5,
                    'entry_price': 50000.0,
                    'current_price': 51000.0,
                    'unrealized_pnl': 500.0,
                    'realized_pnl': 0.0,
                    'margin_used': 25000.0,
                    'leverage': 2.0,
                    'side': 'long'
                },
                {
                    'symbol': 'ETH',
                    'size': 2.0,
                    'entry_price': 3000.0,
                    'current_price': 3100.0,
                    'unrealized_pnl': 200.0,
                    'realized_pnl': 0.0,
                    'margin_used': 15000.0,
                    'leverage': 2.0,
                    'side': 'long'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting positions from API: {e}")
            return []
    
    async def _calculate_portfolio_state(self, user_state: Dict[str, Any], positions: List[Dict[str, Any]]) -> PortfolioState:
        """Calculate portfolio state from user state and positions."""
        try:
            # Convert positions to Position objects
            position_objects = []
            for pos_data in positions:
                position = Position(
                    symbol=pos_data['symbol'],
                    size=pos_data['size'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    unrealized_pnl=pos_data['unrealized_pnl'],
                    realized_pnl=pos_data['realized_pnl'],
                    margin_used=pos_data['margin_used'],
                    leverage=pos_data['leverage'],
                    side=pos_data['side']
                )
                position_objects.append(position)
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics(position_objects, user_state)
            
            # Create portfolio state
            portfolio_state = PortfolioState(
                total_value=user_state.get('total_value', 0.0),
                available_margin=user_state.get('available_margin', 0.0),
                used_margin=user_state.get('used_margin', 0.0),
                total_pnl=user_state.get('total_pnl', 0.0),
                positions=position_objects,
                last_updated=datetime.now(timezone.utc),
                risk_metrics=risk_metrics
            )
            
            return portfolio_state
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio state: {e}")
            return PortfolioState(
                total_value=0.0,
                available_margin=0.0,
                used_margin=0.0,
                total_pnl=0.0,
                positions=[],
                last_updated=datetime.now(timezone.utc),
                risk_metrics={}
            )
    
    async def _calculate_risk_metrics(self, positions: List[Position], user_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics for the portfolio."""
        try:
            total_value = user_state.get('total_value', 0.0)
            used_margin = user_state.get('used_margin', 0.0)
            
            # Calculate position concentration
            position_concentration = {}
            for position in positions:
                position_value = abs(position.size * position.current_price)
                concentration = position_value / total_value if total_value > 0 else 0
                position_concentration[position.symbol] = concentration
            
            # Calculate max position concentration
            max_concentration = max(position_concentration.values()) if position_concentration else 0
            
            # Calculate average leverage
            total_leverage = sum(position.leverage for position in positions)
            avg_leverage = total_leverage / len(positions) if positions else 0
            
            # Calculate margin ratio
            margin_ratio = used_margin / total_value if total_value > 0 else 0
            
            return {
                'position_concentration': position_concentration,
                'max_concentration': max_concentration,
                'average_leverage': avg_leverage,
                'margin_ratio': margin_ratio,
                'total_positions': len(positions),
                'risk_score': self._calculate_risk_score(max_concentration, avg_leverage, margin_ratio)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def _calculate_risk_score(self, max_concentration: float, avg_leverage: float, margin_ratio: float) -> float:
        """Calculate overall risk score."""
        try:
            # Risk score based on concentration, leverage, and margin
            concentration_risk = min(max_concentration / 0.1, 1.0)  # 10% = max risk
            leverage_risk = min(avg_leverage / 3.0, 1.0)  # 3x = max risk
            margin_risk = min(margin_ratio / 0.8, 1.0)  # 80% = max risk
            
            # Weighted average
            risk_score = (concentration_risk * 0.4 + leverage_risk * 0.3 + margin_risk * 0.3)
            return min(risk_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return 0.5
    
    async def _update_portfolio_state_from_websocket(self, data: Dict[str, Any]):
        """Update portfolio state from WebSocket data."""
        try:
            if not self.current_portfolio_state:
                return
            
            # Update specific fields based on WebSocket data
            if 'total_value' in data:
                self.current_portfolio_state.total_value = data['total_value']
            if 'available_margin' in data:
                self.current_portfolio_state.available_margin = data['available_margin']
            if 'used_margin' in data:
                self.current_portfolio_state.used_margin = data['used_margin']
            if 'total_pnl' in data:
                self.current_portfolio_state.total_pnl = data['total_pnl']
            
            # Update positions if provided
            if 'positions' in data:
                positions = []
                for pos_data in data['positions']:
                    position = Position(
                        symbol=pos_data['symbol'],
                        size=pos_data['size'],
                        entry_price=pos_data['entry_price'],
                        current_price=pos_data['current_price'],
                        unrealized_pnl=pos_data['unrealized_pnl'],
                        realized_pnl=pos_data['realized_pnl'],
                        margin_used=pos_data['margin_used'],
                        leverage=pos_data['leverage'],
                        side=pos_data['side']
                    )
                    positions.append(position)
                self.current_portfolio_state.positions = positions
            
            # Update timestamp
            self.current_portfolio_state.last_updated = datetime.now(timezone.utc)
            
            # Recalculate risk metrics
            self.current_portfolio_state.risk_metrics = await self._calculate_risk_metrics(
                self.current_portfolio_state.positions,
                {
                    'total_value': self.current_portfolio_state.total_value,
                    'used_margin': self.current_portfolio_state.used_margin
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio state from WebSocket: {e}")
    
    async def _check_risk_alerts(self):
        """Check for risk alerts based on current portfolio state."""
        try:
            if not self.current_portfolio_state:
                return
            
            risk_metrics = self.current_portfolio_state.risk_metrics
            
            # Check max concentration
            if risk_metrics.get('max_concentration', 0) > self.risk_thresholds['max_position_size']:
                await self._trigger_risk_alert('high_concentration', {
                    'max_concentration': risk_metrics['max_concentration'],
                    'threshold': self.risk_thresholds['max_position_size']
                })
            
            # Check average leverage
            if risk_metrics.get('average_leverage', 0) > self.risk_thresholds['max_leverage']:
                await self._trigger_risk_alert('high_leverage', {
                    'average_leverage': risk_metrics['average_leverage'],
                    'threshold': self.risk_thresholds['max_leverage']
                })
            
            # Check margin ratio
            if risk_metrics.get('margin_ratio', 0) > (1 - self.risk_thresholds['min_margin_ratio']):
                await self._trigger_risk_alert('low_margin', {
                    'margin_ratio': risk_metrics['margin_ratio'],
                    'threshold': 1 - self.risk_thresholds['min_margin_ratio']
                })
            
        except Exception as e:
            self.logger.error(f"Error checking risk alerts: {e}")
    
    async def _trigger_risk_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger a risk alert."""
        try:
            alert = {
                'type': alert_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'portfolio_state': self.current_portfolio_state
            }
            
            self.logger.warning(f"Risk alert triggered: {alert_type} - {data}")
            
            # Notify callbacks
            await self._notify_risk_alert_callbacks(alert)
            
        except Exception as e:
            self.logger.error(f"Error triggering risk alert: {e}")
    
    async def _notify_portfolio_update_callbacks(self):
        """Notify portfolio update callbacks."""
        try:
            for callback in self.portfolio_update_callbacks:
                try:
                    await callback(self.current_portfolio_state)
                except Exception as e:
                    self.logger.error(f"Error in portfolio update callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error notifying portfolio update callbacks: {e}")
    
    async def _notify_risk_alert_callbacks(self, alert: Dict[str, Any]):
        """Notify risk alert callbacks."""
        try:
            for callback in self.risk_alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in risk alert callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error notifying risk alert callbacks: {e}")
    
    def add_portfolio_update_callback(self, callback: Callable):
        """Add a callback for portfolio updates."""
        self.portfolio_update_callbacks.append(callback)
        self.logger.info("Added portfolio update callback")
    
    def add_risk_alert_callback(self, callback: Callable):
        """Add a callback for risk alerts."""
        self.risk_alert_callbacks.append(callback)
        self.logger.info("Added risk alert callback")
    
    def remove_portfolio_update_callback(self, callback: Callable):
        """Remove a portfolio update callback."""
        if callback in self.portfolio_update_callbacks:
            self.portfolio_update_callbacks.remove(callback)
            self.logger.info("Removed portfolio update callback")
    
    def remove_risk_alert_callback(self, callback: Callable):
        """Remove a risk alert callback."""
        if callback in self.risk_alert_callbacks:
            self.risk_alert_callbacks.remove(callback)
            self.logger.info("Removed risk alert callback")
    
    async def get_current_portfolio_state(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        return self.current_portfolio_state
    
    async def get_portfolio_history(self, hours: int = 24) -> List[PortfolioState]:
        """Get portfolio history for specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            state for state in self.portfolio_history
            if state.last_updated > cutoff_time
        ]
    
    def get_integration_summary(self) -> Dict[str, Any]:
        """Get summary of portfolio data integration."""
        return {
            'websocket_connected': self.websocket_connected,
            'current_portfolio_value': self.current_portfolio_state.total_value if self.current_portfolio_state else 0,
            'total_positions': len(self.current_portfolio_state.positions) if self.current_portfolio_state else 0,
            'portfolio_history_count': len(self.portfolio_history),
            'portfolio_update_callbacks': len(self.portfolio_update_callbacks),
            'risk_alert_callbacks': len(self.risk_alert_callbacks),
            'last_updated': self.current_portfolio_state.last_updated.isoformat() if self.current_portfolio_state else None
        }
