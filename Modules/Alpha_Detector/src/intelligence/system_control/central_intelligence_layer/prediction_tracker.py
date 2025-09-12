"""
Prediction Tracker for CIL Learning System

This module tracks all trading predictions until max_time expires.
It monitors prediction outcomes and provides data for learning analysis.

Features:
1. Track prediction lifecycle (creation, updates, finalization)
2. Monitor current price, max drawdown, time remaining
3. Finalize predictions with outcomes
4. Provide data for outcome analysis
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class PredictionStatus(Enum):
    """Prediction tracking status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PredictionOutcome(Enum):
    """Prediction outcome types"""
    TARGET_HIT = "target_hit"
    STOP_HIT = "stop_hit"
    EXPIRED = "expired"
    MAX_DRAWDOWN_ACHIEVED = "max_drawdown_achieved"
    CANCELLED = "cancelled"


@dataclass
class PredictionData:
    """Prediction tracking data"""
    prediction_id: str
    symbol: str
    timeframe: str
    entry_price: float
    target_price: float
    stop_loss: float
    max_time: int  # minutes
    created_at: datetime
    status: PredictionStatus
    current_price: Optional[float] = None
    max_drawdown: float = 0.0
    time_remaining: Optional[int] = None
    outcome: Optional[PredictionOutcome] = None
    final_price: Optional[float] = None
    final_at: Optional[datetime] = None


class PredictionTracker:
    """
    Tracks all predictions until max_time expires
    
    This is a new Raw Team Member that monitors trading predictions
    and provides data for the CIL learning system.
    """
    
    def __init__(self, supabase_manager):
        """
        Initialize prediction tracker
        
        Args:
            supabase_manager: Database manager for persistence
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Active predictions cache
        self.active_predictions: Dict[str, PredictionData] = {}
        
        # Tracking configuration
        self.update_interval_minutes = 5
        self.max_tracking_days = 7  # Maximum days to track a prediction
    
    async def track_prediction(self, prediction_strand: Dict[str, Any]) -> bool:
        """
        Track a new prediction
        
        Args:
            prediction_strand: Strand dictionary with prediction data
            
        Returns:
            True if tracking started successfully, False otherwise
        """
        try:
            # Extract prediction data from strand
            prediction_data = self._extract_prediction_data(prediction_strand)
            
            if not prediction_data:
                self.logger.error("Failed to extract prediction data from strand")
                return False
            
            # Store in active predictions
            self.active_predictions[prediction_data.prediction_id] = prediction_data
            
            # Save to database
            await self._save_prediction_to_database(prediction_data)
            
            self.logger.info(f"Started tracking prediction {prediction_data.prediction_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error tracking prediction: {e}")
            return False
    
    async def update_prediction_outcome(self, prediction_id: str, current_price: Optional[float] = None) -> bool:
        """
        Update prediction with current price and calculate metrics
        
        Args:
            prediction_id: ID of prediction to update
            current_price: Current market price (optional, will fetch from DB if not provided)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get prediction data from database
            prediction_data = await self._get_prediction_from_db(prediction_id)
            if not prediction_data:
                self.logger.warning(f"Prediction {prediction_id} not found in database")
                return False
            
            # Extract prediction info
            symbol = prediction_data.get('symbol', '')
            timeframe = prediction_data.get('timeframe', '')
            
            # Fetch current price from market data if not provided
            if current_price is None:
                current_price = await self._fetch_current_price(symbol, timeframe)
                if current_price is None:
                    self.logger.warning(f"Could not fetch current price for {symbol} {timeframe}")
                    return False
            
            # Calculate metrics
            entry_price = prediction_data.get('prediction_data', {}).get('entry_price', 0.0)
            max_drawdown = prediction_data.get('prediction_data', {}).get('max_drawdown', 0.0)
            
            # Calculate new max drawdown
            if current_price < entry_price:
                drawdown = (entry_price - current_price) / entry_price
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate time remaining
            created_at = datetime.fromisoformat(prediction_data['created_at'].replace('Z', '+00:00'))
            max_time = prediction_data.get('prediction_data', {}).get('max_time', 60)
            elapsed_minutes = (datetime.now(timezone.utc) - created_at).total_seconds() / 60
            time_remaining = max(0, max_time - int(elapsed_minutes))
            
            # Check if prediction should be finalized
            should_finalize = await self._should_finalize_prediction_db(prediction_data, current_price, time_remaining, max_drawdown)
            if should_finalize:
                outcome = self._determine_outcome_db(prediction_data, current_price, time_remaining, max_drawdown)
                await self.finalize_prediction(prediction_id, outcome)
                return True
            
            # Update prediction in database
            await self._update_prediction_in_database(prediction_id, current_price, max_drawdown, time_remaining)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating prediction {prediction_id}: {e}")
            return False
    
    async def finalize_prediction(self, prediction_id: str, outcome: PredictionOutcome) -> bool:
        """
        Finalize a prediction with its outcome
        
        Args:
            prediction_id: ID of prediction to finalize
            outcome: Final outcome of the prediction
            
        Returns:
            True if finalized successfully, False otherwise
        """
        try:
            if prediction_id not in self.active_predictions:
                self.logger.warning(f"Prediction {prediction_id} not found in active predictions")
                return False
            
            prediction = self.active_predictions[prediction_id]
            
            # Update prediction data
            prediction.status = PredictionStatus.COMPLETED
            prediction.outcome = outcome
            prediction.final_price = prediction.current_price
            prediction.final_at = datetime.now(timezone.utc)
            
            # Remove from active predictions
            del self.active_predictions[prediction_id]
            
            # Update database
            await self._finalize_prediction_in_database(prediction)
            
            self.logger.info(f"Finalized prediction {prediction_id} with outcome {outcome.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error finalizing prediction {prediction_id}: {e}")
            return False
    
    async def get_prediction_data(self, prediction_id: str) -> Optional[PredictionData]:
        """
        Get prediction data by ID
        
        Args:
            prediction_id: ID of prediction
            
        Returns:
            PredictionData if found, None otherwise
        """
        return self.active_predictions.get(prediction_id)
    
    async def get_active_predictions(self) -> List[PredictionData]:
        """
        Get all active predictions
        
        Returns:
            List of active PredictionData objects
        """
        return list(self.active_predictions.values())
    
    async def update_all_predictions(self) -> int:
        """
        Update all active predictions with current market prices
        
        This method loads active predictions from the database rather than
        relying on the in-memory cache, making it more robust.
        
        Returns:
            Number of predictions updated successfully
        """
        try:
            # Get active predictions from database
            active_predictions = await self._get_active_predictions_from_db()
            updated_count = 0
            
            for prediction_data in active_predictions:
                prediction_id = prediction_data['id']
                success = await self.update_prediction_outcome(prediction_id)
                if success:
                    updated_count += 1
            
            self.logger.info(f"Updated {updated_count} active predictions")
            return updated_count
            
        except Exception as e:
            self.logger.error(f"Error updating all predictions: {e}")
            return 0
    
    async def cleanup_expired_predictions(self) -> int:
        """
        Clean up expired predictions that haven't been finalized
        
        Returns:
            Number of predictions cleaned up
        """
        try:
            current_time = datetime.now(timezone.utc)
            expired_predictions = []
            
            for prediction_id, prediction in self.active_predictions.items():
                # Check if prediction has exceeded max time
                elapsed_minutes = (current_time - prediction.created_at).total_seconds() / 60
                if elapsed_minutes > prediction.max_time:
                    expired_predictions.append(prediction_id)
            
            # Finalize expired predictions
            for prediction_id in expired_predictions:
                await self.finalize_prediction(prediction_id, PredictionOutcome.EXPIRED)
            
            self.logger.info(f"Cleaned up {len(expired_predictions)} expired predictions")
            return len(expired_predictions)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired predictions: {e}")
            return 0
    
    async def _fetch_current_price(self, symbol: str, timeframe: str) -> Optional[float]:
        """
        Fetch current price from market data tables
        
        Args:
            symbol: Trading symbol (e.g., 'BTC')
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            
        Returns:
            Current price if found, None otherwise
        """
        try:
            # Map timeframe to table name
            table_mapping = {
                '1m': 'alpha_market_data_1m',
                '5m': 'alpha_market_data_5m',
                '15m': 'alpha_market_data_15m',
                '1h': 'alpha_market_data_1h',
                '4h': 'alpha_market_data_4h'
            }
            
            table_name = table_mapping.get(timeframe)
            if not table_name:
                self.logger.error(f"Unsupported timeframe: {timeframe}")
                return None
            
            # Query for latest price
            result = self.supabase_manager.client.table(table_name).select('close').eq('symbol', symbol).order('timestamp', desc=True).limit(1).execute()
            
            if result.data and len(result.data) > 0:
                return float(result.data[0]['close'])
            else:
                self.logger.warning(f"No market data found for {symbol} {timeframe}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching current price for {symbol} {timeframe}: {e}")
            return None
    
    async def _get_active_predictions_from_db(self) -> List[Dict[str, Any]]:
        """
        Get active predictions from database
        
        Returns:
            List of active prediction data from database
        """
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').eq('tracking_status', 'active').execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting active predictions from database: {e}")
            return []
    
    async def _get_prediction_from_db(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get prediction data from database
        
        Args:
            prediction_id: ID of prediction
            
        Returns:
            Prediction data if found, None otherwise
        """
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', prediction_id).eq('kind', 'prediction').execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting prediction from database: {e}")
            return None
    
    async def _should_finalize_prediction_db(self, prediction_data: Dict[str, Any], current_price: float, time_remaining: int, max_drawdown: float) -> bool:
        """
        Check if prediction should be finalized (database version)
        
        Args:
            prediction_data: Prediction data from database
            current_price: Current market price
            time_remaining: Time remaining in minutes
            max_drawdown: Current max drawdown
            
        Returns:
            True if should be finalized, False otherwise
        """
        try:
            prediction_info = prediction_data.get('prediction_data', {})
            target_price = prediction_info.get('target_price', 0.0)
            stop_loss = prediction_info.get('stop_loss', 0.0)
            
            # Check if target hit
            if current_price >= target_price:
                return True
            
            # Check if stop loss hit
            if current_price <= stop_loss:
                return True
            
            # Check if time expired
            if time_remaining <= 0:
                return True
            
            # Check if max drawdown exceeded (optional)
            if max_drawdown > 0.15:  # 15% max drawdown threshold
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if prediction should be finalized: {e}")
            return False
    
    def _determine_outcome_db(self, prediction_data: Dict[str, Any], current_price: float, time_remaining: int, max_drawdown: float) -> PredictionOutcome:
        """
        Determine prediction outcome (database version)
        
        Args:
            prediction_data: Prediction data from database
            current_price: Current market price
            time_remaining: Time remaining in minutes
            max_drawdown: Current max drawdown
            
        Returns:
            PredictionOutcome
        """
        try:
            prediction_info = prediction_data.get('prediction_data', {})
            target_price = prediction_info.get('target_price', 0.0)
            stop_loss = prediction_info.get('stop_loss', 0.0)
            
            # Check target hit
            if current_price >= target_price:
                return PredictionOutcome.TARGET_HIT
            
            # Check stop loss hit
            if current_price <= stop_loss:
                return PredictionOutcome.STOP_HIT
            
            # Check time expired
            if time_remaining <= 0:
                return PredictionOutcome.EXPIRED
            
            # Check max drawdown
            if max_drawdown > 0.15:
                return PredictionOutcome.MAX_DRAWDOWN_ACHIEVED
            
            return PredictionOutcome.EXPIRED
            
        except Exception as e:
            self.logger.error(f"Error determining outcome: {e}")
            return PredictionOutcome.EXPIRED
    
    async def _update_prediction_in_database(self, prediction_id: str, current_price: float, max_drawdown: float, time_remaining: int) -> bool:
        """
        Update prediction in database with new metrics
        
        Args:
            prediction_id: ID of prediction to update
            current_price: Current market price
            max_drawdown: Current max drawdown
            time_remaining: Time remaining in minutes
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get current prediction data
            prediction_data = await self._get_prediction_from_db(prediction_id)
            if not prediction_data:
                return False
            
            # Update prediction data
            updated_prediction_data = prediction_data.get('prediction_data', {}).copy()
            updated_prediction_data.update({
                'current_price': current_price,
                'max_drawdown': max_drawdown,
                'time_remaining': time_remaining
            })
            
            result = self.supabase_manager.client.table('ad_strands').update({
                'prediction_data': updated_prediction_data
            }).eq('id', prediction_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error updating prediction in database: {e}")
            return False
    
    def _extract_prediction_data(self, strand: Dict[str, Any]) -> Optional[PredictionData]:
        """
        Extract prediction data from strand
        
        Args:
            strand: Strand dictionary
            
        Returns:
            PredictionData if extraction successful, None otherwise
        """
        try:
            prediction_data = strand.get('prediction_data', {})
            
            if not prediction_data:
                return None
            
            return PredictionData(
                prediction_id=strand['id'],
                symbol=strand.get('symbol', ''),
                timeframe=strand.get('timeframe', ''),
                entry_price=prediction_data.get('entry_price', 0.0),
                target_price=prediction_data.get('target_price', 0.0),
                stop_loss=prediction_data.get('stop_loss', 0.0),
                max_time=prediction_data.get('max_time', 60),  # Default 1 hour
                created_at=datetime.now(timezone.utc),
                status=PredictionStatus.ACTIVE
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting prediction data: {e}")
            return None
    
    async def _should_finalize_prediction(self, prediction: PredictionData) -> bool:
        """
        Check if prediction should be finalized
        
        Args:
            prediction: Prediction data
            
        Returns:
            True if should be finalized, False otherwise
        """
        if not prediction.current_price:
            return False
        
        # Check if target hit
        if prediction.current_price >= prediction.target_price:
            return True
        
        # Check if stop loss hit
        if prediction.current_price <= prediction.stop_loss:
            return True
        
        # Check if time expired
        if prediction.time_remaining and prediction.time_remaining <= 0:
            return True
        
        # Check if max drawdown exceeded (optional)
        if prediction.max_drawdown > 0.15:  # 15% max drawdown threshold
            return True
        
        return False
    
    def _determine_outcome(self, prediction: PredictionData) -> PredictionOutcome:
        """
        Determine prediction outcome
        
        Args:
            prediction: Prediction data
            
        Returns:
            PredictionOutcome
        """
        if not prediction.current_price:
            return PredictionOutcome.EXPIRED
        
        # Check target hit
        if prediction.current_price >= prediction.target_price:
            return PredictionOutcome.TARGET_HIT
        
        # Check stop loss hit
        if prediction.current_price <= prediction.stop_loss:
            return PredictionOutcome.STOP_HIT
        
        # Check time expired
        if prediction.time_remaining and prediction.time_remaining <= 0:
            return PredictionOutcome.EXPIRED
        
        # Check max drawdown
        if prediction.max_drawdown > 0.15:
            return PredictionOutcome.MAX_DRAWDOWN_ACHIEVED
        
        return PredictionOutcome.EXPIRED
    
    async def _save_prediction_to_database(self, prediction: PredictionData) -> bool:
        """
        Save prediction to database
        
        Args:
            prediction: Prediction data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Update strand with prediction data
            prediction_data = {
                'entry_price': prediction.entry_price,
                'target_price': prediction.target_price,
                'stop_loss': prediction.stop_loss,
                'max_time': prediction.max_time,
                'current_price': prediction.current_price,
                'max_drawdown': prediction.max_drawdown,
                'time_remaining': prediction.time_remaining,
                'status': prediction.status.value,
                'created_at': prediction.created_at.isoformat()
            }
            
            # Update strand in database
            result = self.supabase_manager.client.table('ad_strands').update({
                'prediction_data': prediction_data,
                'tracking_status': prediction.status.value
            }).eq('id', prediction.prediction_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error saving prediction to database: {e}")
            return False
    
    async def _update_prediction_in_database(self, prediction: PredictionData) -> bool:
        """
        Update prediction in database
        
        Args:
            prediction: Prediction data to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            prediction_data = {
                'current_price': prediction.current_price,
                'max_drawdown': prediction.max_drawdown,
                'time_remaining': prediction.time_remaining,
                'status': prediction.status.value
            }
            
            result = self.supabase_manager.client.table('ad_strands').update({
                'prediction_data': prediction_data,
                'tracking_status': prediction.status.value
            }).eq('id', prediction.prediction_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error updating prediction in database: {e}")
            return False
    
    async def _finalize_prediction_in_database(self, prediction: PredictionData) -> bool:
        """
        Finalize prediction in database
        
        Args:
            prediction: Prediction data to finalize
            
        Returns:
            True if finalized successfully, False otherwise
        """
        try:
            outcome_data = {
                'outcome': prediction.outcome.value if prediction.outcome else None,
                'final_price': prediction.final_price,
                'final_at': prediction.final_at.isoformat() if prediction.final_at else None,
                'max_drawdown': prediction.max_drawdown,
                'duration_minutes': (prediction.final_at - prediction.created_at).total_seconds() / 60 if prediction.final_at else None
            }
            
            result = self.supabase_manager.client.table('ad_strands').update({
                'outcome_data': outcome_data,
                'tracking_status': prediction.status.value
            }).eq('id', prediction.prediction_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error finalizing prediction in database: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test the prediction tracker
    from src.utils.supabase_manager import SupabaseManager
    
    async def test_prediction_tracker():
        supabase_manager = SupabaseManager()
        tracker = PredictionTracker(supabase_manager)
        
        # Test prediction strand
        prediction_strand = {
            'id': 'prediction_test_1',
            'kind': 'prediction',
            'symbol': 'BTC',
            'timeframe': '1h',
            'prediction_data': {
                'entry_price': 50000.0,
                'target_price': 52000.0,
                'stop_loss': 48000.0,
                'max_time': 120  # 2 hours
            }
        }
        
        # Test tracking
        success = await tracker.track_prediction(prediction_strand)
        print(f"Prediction tracking started: {success}")
        
        # Test update
        success = await tracker.update_prediction_outcome('prediction_test_1', 51000.0)
        print(f"Prediction updated: {success}")
        
        # Test finalization
        success = await tracker.finalize_prediction('prediction_test_1', PredictionOutcome.TARGET_HIT)
        print(f"Prediction finalized: {success}")
    
    import asyncio
    asyncio.run(test_prediction_tracker())
