"""
Test suite for CIL PredictionOutcomeTracker

Tests the prediction tracking system that monitors ALL predictions
(not just executed trades) and validates them against market outcomes.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.engines.prediction_outcome_tracker import (
    PredictionOutcomeTracker, PredictionOutcome, PredictionStatus
)


class TestPredictionOutcomeTracker:
    """Test the PredictionOutcomeTracker system"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        db_manager = Mock()
        db_manager.execute_query = AsyncMock()
        db_manager.update_record = AsyncMock()
        db_manager.insert_record = AsyncMock()
        return db_manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        return Mock()
    
    @pytest.fixture
    def tracker(self, mock_db_manager, mock_llm_client):
        """Create PredictionOutcomeTracker instance"""
        return PredictionOutcomeTracker(mock_db_manager, mock_llm_client)
    
    @pytest.mark.asyncio
    async def test_get_pending_predictions(self, tracker, mock_db_manager):
        """Test getting pending predictions from database"""
        # Mock database response
        mock_predictions = [
            {
                'id': 'strand_1',
                'symbol': 'BTC',
                'timeframe': '1h',
                'sig_sigma': 0.8,
                'sig_confidence': 0.7,
                'sig_direction': 'long',
                'created_at': datetime.now(timezone.utc) - timedelta(minutes=30),
                'prediction_score': None,
                'outcome_score': None,
                'tags': ['test']
            },
            {
                'id': 'strand_2',
                'symbol': 'ETH',
                'timeframe': '4h',
                'sig_sigma': 0.6,
                'sig_confidence': 0.5,
                'sig_direction': 'short',
                'created_at': datetime.now(timezone.utc) - timedelta(hours=2),
                'prediction_score': None,
                'outcome_score': None,
                'tags': ['test']
            }
        ]
        
        mock_db_manager.execute_query.return_value = mock_predictions
        
        # Test getting pending predictions
        predictions = await tracker._get_pending_predictions()
        
        assert len(predictions) == 2
        assert predictions[0]['id'] == 'strand_1'
        assert predictions[1]['id'] == 'strand_2'
        mock_db_manager.execute_query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_timeframe_to_hours(self, tracker):
        """Test timeframe conversion to hours"""
        assert tracker._timeframe_to_hours('1m') == 1/60
        assert tracker._timeframe_to_hours('5m') == 5/60
        assert tracker._timeframe_to_hours('15m') == 15/60
        assert tracker._timeframe_to_hours('1h') == 1
        assert tracker._timeframe_to_hours('4h') == 4
        assert tracker._timeframe_to_hours('1d') == 24
        assert tracker._timeframe_to_hours('unknown') == 1.0  # default
    
    @pytest.mark.asyncio
    async def test_determine_direction(self, tracker):
        """Test market direction determination"""
        assert tracker._determine_direction(1.0) == 'long'    # 1% up
        assert tracker._determine_direction(-1.0) == 'short'  # 1% down
        assert tracker._determine_direction(0.3) == 'neutral' # 0.3% up (below threshold)
        assert tracker._determine_direction(-0.3) == 'neutral' # 0.3% down (below threshold)
        assert tracker._determine_direction(0.0) == 'neutral' # no change
    
    @pytest.mark.asyncio
    async def test_calculate_prediction_accuracy(self, tracker):
        """Test prediction accuracy calculation"""
        # Correct prediction
        accuracy = tracker._calculate_prediction_accuracy('long', 'long', 2.0, 0.8)
        assert accuracy > 0.8  # Should be high for correct prediction
        
        # Wrong prediction
        accuracy = tracker._calculate_prediction_accuracy('long', 'short', -2.0, 0.8)
        assert accuracy < 0.5  # Should be low for wrong prediction
        
        # Neutral prediction
        accuracy = tracker._calculate_prediction_accuracy('neutral', 'long', 1.0, 0.5)
        assert 0.4 <= accuracy <= 0.7  # Should be moderate for neutral
        
        # Strong move bonus
        accuracy = tracker._calculate_prediction_accuracy('long', 'long', 8.0, 0.8)
        assert accuracy > 0.9  # Should be very high for strong correct move
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_accuracy(self, tracker):
        """Test confidence calibration accuracy"""
        # Good calibration: high confidence + high accuracy
        calibration = tracker._calculate_confidence_accuracy(0.8, 0.8, 0.02)
        assert calibration == 1.0
        
        # Good calibration: low confidence + low accuracy
        calibration = tracker._calculate_confidence_accuracy(0.2, 0.2, 0.02)
        assert calibration == 1.0
        
        # Poor calibration: high confidence + low accuracy
        calibration = tracker._calculate_confidence_accuracy(0.8, 0.2, 0.02)
        assert calibration == 0.0
        
        # Poor calibration: low confidence + high accuracy
        calibration = tracker._calculate_confidence_accuracy(0.2, 0.8, 0.02)
        assert calibration == 0.0
        
        # Moderate calibration
        calibration = tracker._calculate_confidence_accuracy(0.5, 0.5, 0.02)
        assert calibration == 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_market_volatility(self, tracker):
        """Test market volatility calculation"""
        price_data = {
            'high': 51000,
            'low': 49000,
            'start_price': 50000
        }
        
        volatility = tracker._calculate_market_volatility(price_data)
        expected_volatility = ((51000 - 49000) / 50000) * 100  # 4%
        assert abs(volatility - expected_volatility) < 0.01
    
    @pytest.mark.asyncio
    async def test_calculate_price_change(self, tracker):
        """Test price change calculation"""
        price_data = {
            'start_price': 50000,
            'end_price': 51000
        }
        
        price_change = tracker._calculate_price_change(price_data)
        expected_change = ((51000 - 50000) / 50000) * 100  # 2%
        assert abs(price_change - expected_change) < 0.01
    
    @pytest.mark.asyncio
    async def test_mock_get_price_data(self, tracker):
        """Test mock price data generation"""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)
        
        price_data = await tracker._mock_get_price_data('BTC', start_time, end_time)
        
        assert 'symbol' in price_data
        assert 'start_price' in price_data
        assert 'end_price' in price_data
        assert 'start_time' in price_data
        assert 'end_time' in price_data
        assert 'high' in price_data
        assert 'low' in price_data
        assert 'volume' in price_data
        
        assert price_data['symbol'] == 'BTC'
        assert price_data['start_time'] == start_time
        assert price_data['end_time'] == end_time
        assert price_data['high'] >= max(price_data['start_price'], price_data['end_price'])
        assert price_data['low'] <= min(price_data['start_price'], price_data['end_price'])
    
    @pytest.mark.asyncio
    async def test_calculate_prediction_outcome(self, tracker):
        """Test complete prediction outcome calculation"""
        prediction = {
            'id': 'strand_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'sig_direction': 'long',
            'sig_confidence': 0.8,
            'created_at': datetime.now(timezone.utc) - timedelta(hours=2)
        }
        
        # Mock price data
        with patch.object(tracker, '_get_price_data') as mock_get_price:
            mock_get_price.return_value = {
                'start_price': 50000,
                'end_price': 51000,
                'high': 51200,
                'low': 49800,
                'volume': 1000
            }
            
            outcome = await tracker._calculate_prediction_outcome(prediction)
            
            assert outcome is not None
            assert outcome.strand_id == 'strand_1'
            assert outcome.predicted_direction == 'long'
            assert outcome.actual_direction == 'long'  # Price went up
            assert outcome.prediction_score > 0.5  # Should be good accuracy
            assert outcome.status == PredictionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_update_prediction_score(self, tracker, mock_db_manager):
        """Test updating prediction score in database"""
        outcome = PredictionOutcome(
            strand_id='strand_1',
            prediction_score=0.8,
            actual_price_change=2.0,
            predicted_direction='long',
            actual_direction='long',
            timeframe_hours=1.0,
            confidence_accuracy=0.9,
            market_volatility=3.0,
            outcome_timestamp=datetime.now(timezone.utc),
            status=PredictionStatus.COMPLETED
        )
        
        await tracker._update_prediction_score('strand_1', outcome)
        
        # Verify database update was called
        mock_db_manager.update_record.assert_called_once()
        update_args = mock_db_manager.update_record.call_args
        
        assert update_args[0][0] == 'AD_strands'  # table name
        assert update_args[0][1] == 'strand_1'    # strand_id
        assert update_args[0][2]['prediction_score'] == 0.8
        
        # Verify learning strand was created
        mock_db_manager.insert_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_prediction_accuracy_stats(self, tracker, mock_db_manager):
        """Test getting prediction accuracy statistics"""
        mock_stats = {
            'total_predictions': 100,
            'avg_accuracy': 0.75,
            'avg_confidence': 0.65,
            'high_accuracy_rate': 0.6,
            'high_confidence_accuracy_rate': 0.55
        }
        
        mock_db_manager.execute_query.return_value = [mock_stats]
        
        stats = await tracker.get_prediction_accuracy_stats()
        
        assert stats['total_predictions'] == 100
        assert stats['avg_accuracy'] == 0.75
        assert stats['avg_confidence'] == 0.65
        assert stats['high_accuracy_rate'] == 0.6
        assert stats['high_confidence_accuracy_rate'] == 0.55
    
    @pytest.mark.asyncio
    async def test_process_prediction(self, tracker):
        """Test processing a single prediction"""
        prediction = {
            'id': 'strand_1',
            'symbol': 'BTC',
            'timeframe': '1h',
            'created_at': datetime.now(timezone.utc) - timedelta(hours=2)  # 2 hours ago
        }
        
        with patch.object(tracker, '_calculate_prediction_outcome') as mock_calc, \
             patch.object(tracker, '_update_prediction_score') as mock_update:
            
            mock_outcome = Mock()
            mock_calc.return_value = mock_outcome
            
            await tracker._process_prediction(prediction)
            
            # Should calculate outcome since 2 hours > 1 hour timeframe
            mock_calc.assert_called_once_with(prediction)
            mock_update.assert_called_once_with('strand_1', mock_outcome)
    
    @pytest.mark.asyncio
    async def test_process_prediction_early(self, tracker):
        """Test processing a prediction that's too early"""
        prediction = {
            'id': 'strand_1',
            'symbol': 'BTC',
            'timeframe': '4h',
            'created_at': datetime.now(timezone.utc) - timedelta(hours=1)  # 1 hour ago, but 4h timeframe
        }
        
        with patch.object(tracker, '_calculate_prediction_outcome') as mock_calc, \
             patch.object(tracker, '_update_prediction_score') as mock_update, \
             patch.object(tracker, '_is_tracking') as mock_tracking, \
             patch.object(tracker, '_start_tracking') as mock_start:
            
            mock_tracking.return_value = False
            
            await tracker._process_prediction(prediction)
            
            # Should not calculate outcome since 1 hour < 4 hour timeframe
            mock_calc.assert_not_called()
            mock_update.assert_not_called()
            
            # Should start tracking
            mock_start.assert_called_once_with('strand_1', 'BTC', '4h')
    
    @pytest.mark.asyncio
    async def test_track_pending_predictions(self, tracker):
        """Test tracking all pending predictions"""
        mock_predictions = [
            {'id': 'strand_1', 'symbol': 'BTC', 'timeframe': '1h', 'created_at': datetime.now(timezone.utc) - timedelta(hours=2)},
            {'id': 'strand_2', 'symbol': 'ETH', 'timeframe': '4h', 'created_at': datetime.now(timezone.utc) - timedelta(hours=1)}
        ]
        
        with patch.object(tracker, '_get_pending_predictions') as mock_get, \
             patch.object(tracker, '_process_prediction') as mock_process:
            
            mock_get.return_value = mock_predictions
            
            await tracker._track_pending_predictions()
            
            # Should process both predictions
            assert mock_process.call_count == 2
            mock_process.assert_any_call(mock_predictions[0])
            mock_process.assert_any_call(mock_predictions[1])


class TestPredictionOutcomeIntegration:
    """Integration tests for prediction outcome tracking"""
    
    @pytest.mark.asyncio
    async def test_full_prediction_cycle(self):
        """Test complete prediction tracking cycle"""
        # This would be an integration test with real database
        # For now, we'll test the flow with mocks
        
        mock_db_manager = Mock()
        mock_llm_client = Mock()
        
        tracker = PredictionOutcomeTracker(mock_db_manager, mock_llm_client)
        
        # Mock the full cycle
        with patch.object(tracker, '_get_pending_predictions') as mock_get, \
             patch.object(tracker, '_calculate_prediction_outcome') as mock_calc, \
             patch.object(tracker, '_update_prediction_score') as mock_update:
            
            # Setup mocks
            mock_predictions = [{
                'id': 'test_strand',
                'symbol': 'BTC',
                'timeframe': '1h',
                'sig_direction': 'long',
                'sig_confidence': 0.8,
                'created_at': datetime.now(timezone.utc) - timedelta(hours=2)
            }]
            
            mock_outcome = PredictionOutcome(
                strand_id='test_strand',
                prediction_score=0.85,
                actual_price_change=2.5,
                predicted_direction='long',
                actual_direction='long',
                timeframe_hours=1.0,
                confidence_accuracy=0.9,
                market_volatility=2.0,
                outcome_timestamp=datetime.now(timezone.utc),
                status=PredictionStatus.COMPLETED
            )
            
            mock_get.return_value = mock_predictions
            mock_calc.return_value = mock_outcome
            
            # Run the tracking cycle
            await tracker._track_pending_predictions()
            
            # Verify the cycle completed
            mock_get.assert_called_once()
            mock_calc.assert_called_once()
            mock_update.assert_called_once_with('test_strand', mock_outcome)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
