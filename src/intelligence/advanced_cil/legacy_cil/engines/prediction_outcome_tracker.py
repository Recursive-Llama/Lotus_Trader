"""
PredictionOutcomeTracker - CIL Engine for tracking prediction accuracy

This system tracks ALL predictions made by the system (not just executed trades)
and validates them against actual market outcomes to calculate prediction_score.

Key Features:
- Monitors all strands with predictions (sig_sigma + sig_confidence)
- Tracks price movements over prediction timeframes
- Calculates prediction accuracy scores
- Updates prediction_score in original strands
- Feeds into learning system for continuous improvement
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

class PredictionStatus(Enum):
    """Status of prediction tracking"""
    PENDING = "pending"           # Prediction made, waiting for outcome
    TRACKING = "tracking"         # Currently monitoring market
    COMPLETED = "completed"       # Outcome calculated
    EXPIRED = "expired"          # Timeframe passed without clear outcome
    INVALID = "invalid"          # Prediction was invalid/unclear

@dataclass
class PredictionOutcome:
    """Result of prediction validation"""
    strand_id: str
    prediction_score: float
    actual_price_change: float
    predicted_direction: str
    actual_direction: str
    timeframe_hours: float
    confidence_accuracy: float
    market_volatility: float
    outcome_timestamp: datetime
    status: PredictionStatus

class PredictionOutcomeTracker:
    """
    CIL Engine for tracking prediction outcomes against market reality
    
    This system ensures we learn from ALL predictions, not just executed trades.
    """
    
    def __init__(self, db_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.db_manager = db_manager
        self.llm_client = llm_client
        self.tracking_interval = 300  # 5 minutes
        self.max_tracking_hours = 24  # Stop tracking after 24 hours
        
    async def track_prediction(self, prediction_id: str) -> str:
        """Track a specific prediction"""
        try:
            logger.info(f"Starting tracking for prediction: {prediction_id}")
            
            # Get prediction data
            prediction = await self._get_prediction_by_id(prediction_id)
            if not prediction:
                logger.error(f"Prediction {prediction_id} not found")
                return f"error: prediction not found"
            
            # Start tracking
            await self._start_tracking(prediction_id, prediction.get('symbol', 'BTC'), prediction.get('timeframe', '1h'))
            
            return f"tracking started for {prediction_id}"
            
        except Exception as e:
            logger.error(f"Error tracking prediction {prediction_id}: {e}")
            return f"error: {str(e)}"
    
    async def start_prediction_tracking(self):
        """Start the prediction tracking service"""
        logger.info("Starting PredictionOutcomeTracker service")
        
        while True:
            try:
                await self._track_pending_predictions()
                await asyncio.sleep(self.tracking_interval)
            except Exception as e:
                logger.error(f"Error in prediction tracking: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _track_pending_predictions(self):
        """Track all pending predictions"""
        try:
            # Get all strands with predictions that need tracking
            pending_predictions = await self._get_pending_predictions()
            
            for prediction in pending_predictions:
                await self._process_prediction(prediction)
                
        except Exception as e:
            logger.error(f"Error tracking pending predictions: {e}")
    
    async def _get_pending_predictions(self) -> List[Dict[str, Any]]:
        """Get all strands with predictions that need outcome tracking"""
        try:
            # Query for strands with predictions but no prediction_score
            query = """
            SELECT id, symbol, timeframe, sig_sigma, sig_confidence, sig_direction,
                   created_at, prediction_score, outcome_score, tags
            FROM AD_strands 
            WHERE sig_sigma > 0 
            AND sig_confidence > 0 
            AND prediction_score IS NULL
            AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            """
            
            result = await self.db_manager.execute_query(query)
            return result if result else []
            
        except Exception as e:
            logger.error(f"Error getting pending predictions: {e}")
            return []
    
    async def _process_prediction(self, prediction: Dict[str, Any]):
        """Process a single prediction for outcome tracking"""
        try:
            strand_id = prediction['id']
            symbol = prediction['symbol']
            timeframe = prediction['timeframe']
            created_at = prediction['created_at']
            
            # Calculate how much time has passed
            time_elapsed = datetime.now(timezone.utc) - created_at
            timeframe_hours = self._timeframe_to_hours(timeframe)
            
            # Check if we should calculate outcome now
            if time_elapsed.total_seconds() >= timeframe_hours * 3600:
                # Timeframe has passed, calculate outcome
                outcome = await self._calculate_prediction_outcome(prediction)
                if outcome:
                    await self._update_prediction_score(strand_id, outcome)
            else:
                # Still tracking, check if we should start monitoring
                if not await self._is_tracking(strand_id):
                    await self._start_tracking(strand_id, symbol, timeframe)
                    
        except Exception as e:
            logger.error(f"Error processing prediction {prediction.get('id', 'unknown')}: {e}")
    
    async def _calculate_prediction_outcome(self, prediction: Dict[str, Any]) -> Optional[PredictionOutcome]:
        """Calculate the outcome of a prediction"""
        try:
            strand_id = prediction['id']
            symbol = prediction['symbol']
            timeframe = prediction['timeframe']
            created_at = prediction['created_at']
            predicted_direction = prediction['sig_direction']
            confidence = prediction['sig_confidence']
            
            # Get price data for the prediction timeframe
            price_data = await self._get_price_data(symbol, created_at, timeframe)
            if not price_data:
                return None
            
            # Calculate actual price movement
            actual_price_change = self._calculate_price_change(price_data)
            actual_direction = self._determine_direction(actual_price_change)
            
            # Calculate prediction accuracy
            prediction_score = self._calculate_prediction_accuracy(
                predicted_direction, actual_direction, actual_price_change, confidence
            )
            
            # Calculate market volatility for context
            market_volatility = self._calculate_market_volatility(price_data)
            
            # Calculate confidence accuracy (how well confidence matched outcome)
            confidence_accuracy = self._calculate_confidence_accuracy(
                confidence, prediction_score, market_volatility
            )
            
            return PredictionOutcome(
                strand_id=strand_id,
                prediction_score=prediction_score,
                actual_price_change=actual_price_change,
                predicted_direction=predicted_direction,
                actual_direction=actual_direction,
                timeframe_hours=self._timeframe_to_hours(timeframe),
                confidence_accuracy=confidence_accuracy,
                market_volatility=market_volatility,
                outcome_timestamp=datetime.now(timezone.utc),
                status=PredictionStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Error calculating prediction outcome: {e}")
            return None
    
    async def _get_price_data(self, symbol: str, start_time: datetime, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get price data for the prediction timeframe"""
        try:
            # Calculate end time based on timeframe
            timeframe_hours = self._timeframe_to_hours(timeframe)
            end_time = start_time + timedelta(hours=timeframe_hours)
            
            # Query price data (this would connect to your market data source)
            # For now, we'll simulate this with a mock
            return await self._mock_get_price_data(symbol, start_time, end_time)
            
        except Exception as e:
            logger.error(f"Error getting price data for {symbol}: {e}")
            return None
    
    async def _mock_get_price_data(self, symbol: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Mock price data - replace with real market data source"""
        # This would be replaced with actual market data API calls
        import random
        
        # Simulate price movement
        base_price = 50000.0  # Mock BTC price
        volatility = 0.02  # 2% volatility
        
        start_price = base_price * (1 + random.uniform(-volatility, volatility))
        end_price = start_price * (1 + random.uniform(-volatility * 2, volatility * 2))
        
        return {
            'symbol': symbol,
            'start_price': start_price,
            'end_price': end_price,
            'start_time': start_time,
            'end_time': end_time,
            'high': max(start_price, end_price) * 1.01,
            'low': min(start_price, end_price) * 0.99,
            'volume': random.uniform(1000, 5000)
        }
    
    def _calculate_price_change(self, price_data: Dict[str, Any]) -> float:
        """Calculate percentage price change"""
        start_price = price_data['start_price']
        end_price = price_data['end_price']
        return ((end_price - start_price) / start_price) * 100
    
    def _determine_direction(self, price_change: float) -> str:
        """Determine market direction from price change"""
        if price_change > 0.5:  # 0.5% threshold
            return 'long'
        elif price_change < -0.5:
            return 'short'
        else:
            return 'neutral'
    
    def _calculate_prediction_accuracy(self, predicted: str, actual: str, 
                                     price_change: float, confidence: float) -> float:
        """Calculate prediction accuracy score (0.0-1.0)"""
        # Base accuracy from direction match
        if predicted == actual:
            base_accuracy = 1.0
        elif predicted == 'neutral' or actual == 'neutral':
            base_accuracy = 0.5  # Partial credit for neutral
        else:
            base_accuracy = 0.0  # Wrong direction
        
        # Adjust for magnitude (stronger moves get higher scores)
        magnitude_bonus = min(abs(price_change) / 5.0, 0.2)  # Up to 20% bonus for strong moves
        
        # Adjust for confidence calibration
        confidence_bonus = 0.0
        if base_accuracy > 0.5 and confidence > 0.7:
            confidence_bonus = 0.1  # Bonus for high confidence correct predictions
        elif base_accuracy < 0.5 and confidence < 0.3:
            confidence_bonus = 0.1  # Bonus for low confidence wrong predictions (good calibration)
        
        final_score = min(1.0, base_accuracy + magnitude_bonus + confidence_bonus)
        return max(0.0, final_score)
    
    def _calculate_confidence_accuracy(self, confidence: float, prediction_score: float, 
                                     volatility: float) -> float:
        """Calculate how well confidence matched the actual outcome"""
        # Good calibration: high confidence + high accuracy OR low confidence + low accuracy
        if (confidence > 0.7 and prediction_score > 0.7) or (confidence < 0.3 and prediction_score < 0.3):
            return 1.0
        elif (confidence > 0.7 and prediction_score < 0.3) or (confidence < 0.3 and prediction_score > 0.7):
            return 0.0
        else:
            return 0.5  # Moderate calibration
    
    def _calculate_market_volatility(self, price_data: Dict[str, Any]) -> float:
        """Calculate market volatility during the period"""
        high = price_data['high']
        low = price_data['low']
        start_price = price_data['start_price']
        
        # Calculate volatility as percentage range
        volatility = ((high - low) / start_price) * 100
        return volatility
    
    def _timeframe_to_hours(self, timeframe: str) -> float:
        """Convert timeframe string to hours"""
        timeframe_map = {
            '1m': 1/60,
            '5m': 5/60,
            '15m': 15/60,
            '1h': 1,
            '4h': 4,
            '1d': 24
        }
        return timeframe_map.get(timeframe, 1.0)
    
    async def _update_prediction_score(self, strand_id: str, outcome: PredictionOutcome):
        """Update the prediction_score in the original strand"""
        try:
            update_data = {
                'prediction_score': outcome.prediction_score,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add outcome details to module_intelligence
            outcome_details = {
                'prediction_outcome': {
                    'actual_price_change': outcome.actual_price_change,
                    'predicted_direction': outcome.predicted_direction,
                    'actual_direction': outcome.actual_direction,
                    'confidence_accuracy': outcome.confidence_accuracy,
                    'market_volatility': outcome.market_volatility,
                    'outcome_timestamp': outcome.outcome_timestamp.isoformat(),
                    'status': outcome.status.value
                }
            }
            
            # Update the strand
            await self.db_manager.update_record('AD_strands', strand_id, update_data)
            
            # Create a learning strand for the outcome
            await self._create_outcome_learning_strand(outcome, outcome_details)
            
            logger.info(f"Updated prediction_score for strand {strand_id}: {outcome.prediction_score}")
            
        except Exception as e:
            logger.error(f"Error updating prediction score for {strand_id}: {e}")
    
    async def _create_outcome_learning_strand(self, outcome: PredictionOutcome, outcome_details: Dict[str, Any]):
        """Create a learning strand for the prediction outcome"""
        try:
            learning_strand = {
                'id': f"prediction_outcome_{outcome.strand_id}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_outcome',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'team_member': 'prediction_outcome_tracker',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:prediction_outcome_tracker:outcome_learned'],
                'module_intelligence': outcome_details,
                'sig_sigma': outcome.prediction_score,
                'sig_confidence': outcome.confidence_accuracy,
                'sig_direction': 'neutral',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self.db_manager.insert_record('AD_strands', learning_strand)
            
        except Exception as e:
            logger.error(f"Error creating outcome learning strand: {e}")
    
    async def _get_prediction_by_id(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Get prediction data by ID"""
        try:
            query = "SELECT * FROM AD_strands WHERE id = %s AND kind = 'prediction'"
            result = await self.db_manager.execute_query(query, [prediction_id])
            
            if result:
                return dict(result[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting prediction {prediction_id}: {e}")
            return None
    
    async def _is_tracking(self, strand_id: str) -> bool:
        """Check if we're already tracking this prediction"""
        # This would check a tracking table or use tags
        # For now, return False to always start tracking
        return False
    
    async def _start_tracking(self, strand_id: str, symbol: str, timeframe: str):
        """Start tracking a prediction"""
        # This would add to a tracking table or update tags
        # For now, just log
        logger.info(f"Started tracking prediction {strand_id} for {symbol} {timeframe}")
    
    async def get_prediction_accuracy_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get prediction accuracy statistics"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_predictions,
                AVG(prediction_score) as avg_accuracy,
                AVG(sig_confidence) as avg_confidence,
                AVG(CASE WHEN prediction_score > 0.7 THEN 1.0 ELSE 0.0 END) as high_accuracy_rate,
                AVG(CASE WHEN sig_confidence > 0.7 AND prediction_score > 0.7 THEN 1.0 ELSE 0.0 END) as high_confidence_accuracy_rate
            FROM AD_strands 
            WHERE prediction_score IS NOT NULL 
            AND created_at > NOW() - INTERVAL '%s hours'
            """ % hours_back
            
            result = await self.db_manager.execute_query(query)
            if result:
                return result[0]
            return {}
            
        except Exception as e:
            logger.error(f"Error getting prediction accuracy stats: {e}")
            return {}


# Test function
async def test_prediction_outcome_tracker():
    """Test the PredictionOutcomeTracker"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    db_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    tracker = PredictionOutcomeTracker(db_manager, llm_client)
    
    # Test prediction accuracy stats
    stats = await tracker.get_prediction_accuracy_stats()
    print("Prediction Accuracy Stats:")
    print(f"Total Predictions: {stats.get('total_predictions', 0)}")
    print(f"Average Accuracy: {stats.get('avg_accuracy', 0):.3f}")
    print(f"Average Confidence: {stats.get('avg_confidence', 0):.3f}")
    print(f"High Accuracy Rate: {stats.get('high_accuracy_rate', 0):.3f}")
    print(f"High Confidence Accuracy Rate: {stats.get('high_confidence_accuracy_rate', 0):.3f}")


if __name__ == "__main__":
    asyncio.run(test_prediction_outcome_tracker())
