"""
Test Meta-Signal System
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone, timedelta

from src.intelligence.system_control.central_intelligence_layer.meta_signals import (
    MetaSignalGenerator, MetaSignal,
    ConfluenceDetector, ConfluenceEvent,
    LeadLagPredictor, LeadLagRelationship,
    TransferHitDetector, TransferHit
)


class TestMetaSignalSystem:
    """Test the complete meta-signal system"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return Mock()
    
    @pytest.fixture
    def meta_signal_generator(self, mock_supabase_manager, mock_llm_client):
        return MetaSignalGenerator(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def confluence_detector(self, mock_supabase_manager):
        return ConfluenceDetector(mock_supabase_manager)
    
    @pytest.fixture
    def lead_lag_predictor(self, mock_supabase_manager):
        return LeadLagPredictor(mock_supabase_manager)
    
    @pytest.fixture
    def transfer_hit_detector(self, mock_supabase_manager):
        return TransferHitDetector(mock_supabase_manager)
    
    def test_meta_signal_generator_initialization(self, meta_signal_generator):
        """Test MetaSignalGenerator initialization"""
        assert meta_signal_generator.meta_signal_types == [
            'confluence_event',
            'lead_lag_predict', 
            'transfer_hit',
            'strategic_confluence',
            'experiment_directive',
            'doctrine_update'
        ]
    
    def test_confluence_detector_initialization(self, confluence_detector):
        """Test ConfluenceDetector initialization"""
        assert confluence_detector.default_time_window == timedelta(minutes=5)
        assert confluence_detector.confluence_threshold == 0.6
        assert confluence_detector.min_agents == 2
    
    def test_lead_lag_predictor_initialization(self, lead_lag_predictor):
        """Test LeadLagPredictor initialization"""
        assert lead_lag_predictor.min_observations == 3
        assert lead_lag_predictor.max_lag_seconds == 300
        assert lead_lag_predictor.consistency_threshold == 0.7
        assert lead_lag_predictor.confidence_threshold == 0.6
    
    def test_transfer_hit_detector_initialization(self, transfer_hit_detector):
        """Test TransferHitDetector initialization"""
        assert transfer_hit_detector.min_transfer_instances == 2
        assert transfer_hit_detector.transfer_threshold == 0.6
        assert transfer_hit_detector.context_similarity_threshold == 0.4
    
    def test_agent_extraction_from_tags(self, confluence_detector):
        """Test agent extraction from tags"""
        tags = ['agent:raw_data_intelligence:pattern_detected', 'other:tag']
        agent = confluence_detector._extract_agent_from_tags(tags)
        assert agent == 'raw_data_intelligence'
        
        # Test with no agent tag
        tags = ['other:tag', 'another:tag']
        agent = confluence_detector._extract_agent_from_tags(tags)
        assert agent is None
    
    def test_pattern_feature_extraction(self, confluence_detector):
        """Test pattern feature extraction"""
        patterns = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {
                    'pattern_type': 'divergence',
                    'signal_strength': 'high'
                }
            }
        ]
        
        features = confluence_detector._extract_pattern_features(patterns)
        
        expected_features = {
            'symbol:BTC',
            'timeframe:1h',
            'regime:high_vol',
            'session:US',
            'pattern_type:divergence',
            'signal_strength:high',
            'tag:agent:test:pattern'
        }
        
        assert features == expected_features
    
    def test_pattern_similarity_calculation(self, confluence_detector):
        """Test pattern similarity calculation"""
        patterns1 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern']
            }
        ]
        
        patterns2 = [
            {
                'symbol': 'BTC',
                'timeframe': '1h',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'tags': ['agent:test:pattern']
            }
        ]
        
        similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns2)
        assert similarity == 1.0  # Perfect similarity
        
        # Test different patterns
        patterns3 = [
            {
                'symbol': 'ETH',
                'timeframe': '4h',
                'regime': 'low_vol',
                'session_bucket': 'EU',
                'tags': ['agent:other:pattern']
            }
        ]
        
        similarity = confluence_detector._calculate_pattern_similarity(patterns1, patterns3)
        assert similarity < 0.5  # Low similarity (not zero due to some common features)
    
    def test_confluence_candidate_detection(self, confluence_detector):
        """Test confluence candidate detection"""
        agent_patterns = {
            'agent1': [
                {
                    'symbol': 'BTC',
                    'timeframe': '1h',
                    'regime': 'high_vol',
                    'session_bucket': 'US',
                    'tags': ['agent:agent1:pattern']
                }
            ],
            'agent2': [
                {
                    'symbol': 'BTC',
                    'timeframe': '1h',
                    'regime': 'high_vol',
                    'session_bucket': 'US',
                    'tags': ['agent:agent2:pattern']
                }
            ]
        }
        
        candidates = confluence_detector._find_confluence_candidates(agent_patterns)
        
        assert len(candidates) == 1
        assert candidates[0]['agents'] == ['agent1', 'agent2']
        assert candidates[0]['confidence'] > 0.6  # Should be above threshold
    
    def test_lead_lag_sequence_building(self, lead_lag_predictor):
        """Test lead-lag sequence building"""
        strands = [
            {
                'id': 'strand1',
                'created_at': '2024-01-15T10:00:00Z',
                'tags': ['agent:agent1:pattern']
            },
            {
                'id': 'strand2',
                'created_at': '2024-01-15T10:02:00Z',
                'tags': ['agent:agent2:pattern']
            }
        ]
        
        sequences = lead_lag_predictor._build_agent_sequences(strands)
        
        assert 'agent1' in sequences
        assert 'agent2' in sequences
        assert len(sequences['agent1']) == 1
        assert len(sequences['agent2']) == 1
    
    def test_lead_lag_analysis(self, lead_lag_predictor):
        """Test lead-lag relationship analysis"""
        # Create test sequences with clear lead-lag relationship
        # Need at least 3 observations to meet min_observations threshold
        lead_sequence = [
            (datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lead:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'}),
            (datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lead:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'}),
            (datetime(2024, 1, 15, 10, 10, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lead:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'})
        ]
        
        lag_sequence = [
            (datetime(2024, 1, 15, 10, 1, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lag:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'}),
            (datetime(2024, 1, 15, 10, 6, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lag:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'}),
            (datetime(2024, 1, 15, 10, 11, 0, tzinfo=timezone.utc), {'symbol': 'BTC', 'tags': ['agent:lag:pattern'], 'timeframe': '1h', 'regime': 'high_vol', 'session_bucket': 'US'})
        ]
        
        relationship = lead_lag_predictor._analyze_lead_lag('lead', lead_sequence, 'lag', lag_sequence)
        
        assert relationship is not None
        assert relationship.lead_agent == 'lead'
        assert relationship.lag_agent == 'lag'
        assert relationship.avg_lag_seconds == 60.0  # 1 minute average lag
        assert relationship.confidence > 0.6
    
    def test_transfer_hit_pattern_grouping(self, transfer_hit_detector):
        """Test transfer hit pattern grouping"""
        strands = [
            {
                'symbol': 'BTC',
                'session_bucket': 'US',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            },
            {
                'symbol': 'ETH',
                'session_bucket': 'EU',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'}
            }
        ]
        
        groups = transfer_hit_detector._group_strands_by_pattern_similarity(strands)
        
        # Should group similar patterns together
        assert len(groups) >= 1
        assert any(len(group) >= 2 for group in groups)
    
    def test_transfer_hit_context_grouping(self, transfer_hit_detector):
        """Test transfer hit context grouping"""
        strands = [
            {
                'symbol': 'BTC',
                'session_bucket': 'US',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern']
            },
            {
                'symbol': 'BTC',
                'session_bucket': 'US',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern']
            },
            {
                'symbol': 'ETH',
                'session_bucket': 'EU',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern']
            }
        ]
        
        context_groups = transfer_hit_detector._group_by_context(strands)
        
        # Should have 2 context groups: BTC/US and ETH/EU
        assert len(context_groups) == 2
        
        # Check context keys (now tuples)
        contexts = list(context_groups.keys())
        btc_context = next(ctx for ctx in contexts if dict(ctx)['symbol'] == 'BTC')
        eth_context = next(ctx for ctx in contexts if dict(ctx)['symbol'] == 'ETH')
        
        assert len(context_groups[btc_context]) == 2
        assert len(context_groups[eth_context]) == 1
    
    def test_transfer_strength_calculation(self, transfer_hit_detector):
        """Test transfer strength calculation"""
        source_strands = [
            {
                'symbol': 'BTC',
                'session_bucket': 'US',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'},
                'sig_sigma': 0.8
            }
        ]
        
        target_strands = [
            {
                'symbol': 'ETH',
                'session_bucket': 'EU',
                'regime': 'high_vol',
                'timeframe': '1h',
                'tags': ['agent:test:pattern'],
                'module_intelligence': {'pattern_type': 'divergence'},
                'sig_sigma': 0.8
            }
        ]
        
        source_context = {'symbol': 'BTC', 'session_bucket': 'US', 'regime': 'high_vol', 'timeframe': '1h'}
        target_context = {'symbol': 'ETH', 'session_bucket': 'EU', 'regime': 'high_vol', 'timeframe': '1h'}
        
        strength = transfer_hit_detector._calculate_transfer_strength(
            source_strands, target_strands, source_context, target_context
        )
        
        assert strength > 0.6  # Should be above threshold
        assert strength <= 1.0  # Should be capped at 1.0
    
    @pytest.mark.asyncio
    async def test_meta_signal_publishing(self, meta_signal_generator):
        """Test meta-signal publishing to database"""
        # Mock supabase manager
        meta_signal_generator.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Create test meta-signal
        signal = MetaSignal(
            signal_id='test_signal_123',
            signal_type='confluence_event',
            source_agents=['agent1', 'agent2'],
            target_agents=['all_teams'],
            confidence=0.8,
            evidence={'test': 'data'},
            created_at=datetime.now(timezone.utc)
        )
        
        result = await meta_signal_generator._publish_meta_signal(signal)
        
        assert result is True
        meta_signal_generator.supabase_manager.insert_strand.assert_called_once()
        
        # Verify call arguments
        call_args = meta_signal_generator.supabase_manager.insert_strand.call_args[0][0]
        assert call_args['id'] == 'test_signal_123'
        assert call_args['kind'] == 'meta_signal'
        assert call_args['strategic_meta_type'] == 'confluence_event'
    
    @pytest.mark.asyncio
    async def test_confluence_event_publishing(self, confluence_detector):
        """Test confluence event publishing to database"""
        # Mock supabase manager
        confluence_detector.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Create test confluence event
        event = ConfluenceEvent(
            event_id='test_confluence_123',
            agents=['agent1', 'agent2'],
            pattern_type='divergence',
            confidence=0.8,
            time_window=timedelta(minutes=5),
            evidence={'test': 'data'},
            created_at=datetime.now(timezone.utc)
        )
        
        result = await confluence_detector._publish_confluence_event(event)
        
        assert result is True
        confluence_detector.supabase_manager.insert_strand.assert_called_once()
        
        # Verify call arguments
        call_args = confluence_detector.supabase_manager.insert_strand.call_args[0][0]
        assert call_args['id'] == 'test_confluence_123'
        assert call_args['kind'] == 'confluence_event'
        assert call_args['strategic_meta_type'] == 'confluence_event'
    
    @pytest.mark.asyncio
    async def test_lead_lag_relationship_publishing(self, lead_lag_predictor):
        """Test lead-lag relationship publishing to database"""
        # Mock supabase manager
        lead_lag_predictor.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Create test lead-lag relationship
        relationship = LeadLagRelationship(
            relationship_id='test_lead_lag_123',
            lead_agent='agent1',
            lag_agent='agent2',
            confidence=0.8,
            avg_lag_seconds=60.0,
            consistency_score=0.9,
            evidence={'test': 'data'},
            created_at=datetime.now(timezone.utc)
        )
        
        result = await lead_lag_predictor._publish_lead_lag_relationship(relationship)
        
        assert result is True
        lead_lag_predictor.supabase_manager.insert_strand.assert_called_once()
        
        # Verify call arguments
        call_args = lead_lag_predictor.supabase_manager.insert_strand.call_args[0][0]
        assert call_args['id'] == 'test_lead_lag_123'
        assert call_args['kind'] == 'lead_lag_relationship'
        assert call_args['strategic_meta_type'] == 'lead_lag_predict'
    
    @pytest.mark.asyncio
    async def test_transfer_hit_publishing(self, transfer_hit_detector):
        """Test transfer hit publishing to database"""
        # Mock supabase manager
        transfer_hit_detector.supabase_manager.insert_strand = AsyncMock(return_value=True)
        
        # Create test transfer hit
        transfer = TransferHit(
            transfer_id='test_transfer_123',
            source_context={'symbol': 'BTC', 'session_bucket': 'US'},
            target_context={'symbol': 'ETH', 'session_bucket': 'EU'},
            pattern_type='divergence',
            confidence=0.8,
            transfer_strength=0.7,
            evidence={'test': 'data'},
            created_at=datetime.now(timezone.utc)
        )
        
        result = await transfer_hit_detector._publish_transfer_hit(transfer)
        
        assert result is True
        transfer_hit_detector.supabase_manager.insert_strand.assert_called_once()
        
        # Verify call arguments
        call_args = transfer_hit_detector.supabase_manager.insert_strand.call_args[0][0]
        assert call_args['id'] == 'test_transfer_123'
        assert call_args['kind'] == 'transfer_hit'
        assert call_args['strategic_meta_type'] == 'transfer_hit'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
