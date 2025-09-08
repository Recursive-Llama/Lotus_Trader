"""
Test CIL Confluence Graph System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.confluence_graph_system import (
    ConfluenceGraphSystem, ConfluenceType, ConfluenceStrength, GraphNodeType,
    ConfluenceNode, ConfluenceEdge, ConfluenceEvent, ConfluenceCluster
)


class TestConfluenceGraphSystem:
    """Test CIL Confluence Graph System"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        return Mock()
    
    @pytest.fixture
    def confluence_system(self, mock_supabase_manager, mock_llm_client):
        """Create ConfluenceGraphSystem instance"""
        return ConfluenceGraphSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_recent_strands(self):
        """Mock recent strands"""
        return [
            {
                'id': 'strand_1',
                'agent_id': 'raw_data_intelligence',
                'pattern_family': 'divergence',
                'signal_type': 'rsi_divergence',
                'timeframe': '1h',
                'symbol': 'BTCUSD',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_confidence': 0.8,
                'sig_sigma': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content': 'RSI divergence detected'
            },
            {
                'id': 'strand_2',
                'agent_id': 'indicator_intelligence',
                'pattern_family': 'volume_anomaly',
                'signal_type': 'volume_spike',
                'timeframe': '1h',
                'symbol': 'BTCUSD',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_confidence': 0.7,
                'sig_sigma': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content': 'Volume spike detected'
            },
            {
                'id': 'strand_3',
                'agent_id': 'pattern_intelligence',
                'pattern_family': 'rejection',
                'signal_type': 'price_rejection',
                'timeframe': '4h',
                'symbol': 'ETHUSD',
                'regime': 'sideways',
                'session_bucket': 'EU',
                'sig_confidence': 0.6,
                'sig_sigma': 0.7,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content': 'Price rejection detected'
            }
        ]
    
    @pytest.fixture
    def mock_global_synthesis_results(self):
        """Mock global synthesis results"""
        return {
            'cross_asset_state': {'BTC': 'bullish', 'ETH': 'neutral'},
            'regime_analysis': {'current_regime': 'high_vol', 'regime_strength': 0.8}
        }
    
    def test_confluence_system_initialization(self, confluence_system):
        """Test ConfluenceGraphSystem initialization"""
        assert confluence_system.supabase_manager is not None
        assert confluence_system.llm_client is not None
        assert confluence_system.confluence_threshold == 0.7
        assert confluence_system.cluster_threshold == 0.8
        assert confluence_system.graph_update_interval_minutes == 5
        assert confluence_system.max_graph_size == 1000
        assert confluence_system.edge_decay_factor == 0.95
        assert confluence_system.confluence_analysis_prompt is not None
        assert confluence_system.cluster_analysis_prompt is not None
        assert confluence_system.graph_optimization_prompt is not None
        assert isinstance(confluence_system.nodes, dict)
        assert isinstance(confluence_system.edges, dict)
        assert isinstance(confluence_system.confluence_events, list)
        assert isinstance(confluence_system.confluence_clusters, list)
    
    def test_load_prompt_templates(self, confluence_system):
        """Test prompt template loading"""
        # Test confluence analysis prompt
        assert 'signals_patterns' in confluence_system.confluence_analysis_prompt
        assert 'timeframe' in confluence_system.confluence_analysis_prompt
        assert 'regime' in confluence_system.confluence_analysis_prompt
        assert 'session' in confluence_system.confluence_analysis_prompt
        assert 'cross_asset_state' in confluence_system.confluence_analysis_prompt
        
        # Test cluster analysis prompt
        assert 'confluence_events' in confluence_system.cluster_analysis_prompt
        assert 'node_count' in confluence_system.cluster_analysis_prompt
        assert 'edge_count' in confluence_system.cluster_analysis_prompt
        assert 'cluster_count' in confluence_system.cluster_analysis_prompt
        
        # Test graph optimization prompt
        assert 'node_count' in confluence_system.graph_optimization_prompt
        assert 'edge_count' in confluence_system.graph_optimization_prompt
        assert 'cluster_count' in confluence_system.graph_optimization_prompt
        assert 'max_size' in confluence_system.graph_optimization_prompt
    
    @pytest.mark.asyncio
    async def test_process_confluence_analysis_success(self, confluence_system, mock_recent_strands, mock_global_synthesis_results):
        """Test successful confluence analysis processing"""
        # Process confluence analysis
        results = await confluence_system.process_confluence_analysis(mock_recent_strands, mock_global_synthesis_results)
        
        # Verify structure
        assert 'confluence_events' in results
        assert 'graph_updates' in results
        assert 'cluster_analysis' in results
        assert 'graph_optimization' in results
        assert 'confluence_timestamp' in results
        assert 'confluence_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['confluence_timestamp'], datetime)
        
        # Verify results are correct types
        assert isinstance(results['confluence_events'], list)
        assert isinstance(results['graph_updates'], dict)
        assert isinstance(results['cluster_analysis'], dict)
        assert isinstance(results['graph_optimization'], dict)
        assert isinstance(results['confluence_errors'], list)
    
    @pytest.mark.asyncio
    async def test_extract_signals_patterns(self, confluence_system, mock_recent_strands):
        """Test signal/pattern extraction from strands"""
        # Extract signals and patterns
        signals_patterns = await confluence_system._extract_signals_patterns(mock_recent_strands)
        
        # Verify results
        assert isinstance(signals_patterns, list)
        assert len(signals_patterns) == 3  # Should extract all 3 strands
        
        # Check signal structure
        for signal in signals_patterns:
            assert 'strand_id' in signal
            assert 'agent_id' in signal
            assert 'pattern_family' in signal
            assert 'signal_type' in signal
            assert 'timeframe' in signal
            assert 'symbol' in signal
            assert 'regime' in signal
            assert 'session_bucket' in signal
            assert 'sig_confidence' in signal
            assert 'sig_sigma' in signal
            assert 'created_at' in signal
            assert 'content' in signal
            
            # Verify specific values
            assert signal['strand_id'] in ['strand_1', 'strand_2', 'strand_3']
            assert signal['agent_id'] in ['raw_data_intelligence', 'indicator_intelligence', 'pattern_intelligence']
            assert signal['pattern_family'] in ['divergence', 'volume_anomaly', 'rejection']
    
    @pytest.mark.asyncio
    async def test_analyze_confluence_events(self, confluence_system, mock_recent_strands, mock_global_synthesis_results):
        """Test confluence event analysis"""
        # Extract signals and patterns first
        signals_patterns = await confluence_system._extract_signals_patterns(mock_recent_strands)
        
        # Analyze confluence events
        confluence_events = await confluence_system._analyze_confluence_events(signals_patterns, mock_global_synthesis_results)
        
        # Verify results
        assert isinstance(confluence_events, list)
        assert len(confluence_events) > 0  # Should detect some confluence events
        
        # Check confluence event structure
        for event in confluence_events:
            assert isinstance(event, ConfluenceEvent)
            assert event.event_id.startswith('CONFLUENCE_')
            assert isinstance(event.confluence_type, ConfluenceType)
            assert isinstance(event.confluence_strength, ConfluenceStrength)
            assert isinstance(event.involved_nodes, list)
            assert 0.0 <= event.confluence_score <= 1.0
            assert isinstance(event.evidence, list)
            assert isinstance(event.timestamp, datetime)
            assert isinstance(event.duration, timedelta)
            assert isinstance(event.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_group_signals_for_confluence(self, confluence_system, mock_recent_strands):
        """Test signal grouping for confluence analysis"""
        # Extract signals and patterns first
        signals_patterns = await confluence_system._extract_signals_patterns(mock_recent_strands)
        
        # Group signals for confluence
        signal_groups = await confluence_system._group_signals_for_confluence(signals_patterns)
        
        # Verify results
        assert isinstance(signal_groups, dict)
        assert len(signal_groups) == 2  # Should have 2 groups: 1h_BTCUSD and 4h_ETHUSD
        
        # Check group structure
        for group_key, group_signals in signal_groups.items():
            assert isinstance(group_key, str)
            assert isinstance(group_signals, list)
            assert len(group_signals) > 0
            
            # Verify all signals in group have same timeframe and symbol
            timeframe, symbol = group_key.split('_', 1)
            for signal in group_signals:
                assert signal['timeframe'] == timeframe
                assert signal['symbol'] == symbol
    
    @pytest.mark.asyncio
    async def test_analyze_group_confluence(self, confluence_system, mock_global_synthesis_results):
        """Test group confluence analysis"""
        # Create test group signals
        group_signals = [
            {
                'strand_id': 'strand_1',
                'agent_id': 'raw_data_intelligence',
                'pattern_family': 'divergence',
                'signal_type': 'rsi_divergence',
                'timeframe': '1h',
                'symbol': 'BTCUSD',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_confidence': 0.8,
                'sig_sigma': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content': 'RSI divergence detected'
            },
            {
                'strand_id': 'strand_2',
                'agent_id': 'indicator_intelligence',
                'pattern_family': 'volume_anomaly',
                'signal_type': 'volume_spike',
                'timeframe': '1h',
                'symbol': 'BTCUSD',
                'regime': 'high_vol',
                'session_bucket': 'US',
                'sig_confidence': 0.7,
                'sig_sigma': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content': 'Volume spike detected'
            }
        ]
        
        # Analyze group confluence
        confluence_events = await confluence_system._analyze_group_confluence(group_signals, mock_global_synthesis_results)
        
        # Verify results
        assert isinstance(confluence_events, list)
        assert len(confluence_events) > 0  # Should detect confluence between the two signals
        
        # Check confluence event structure
        for event in confluence_events:
            assert isinstance(event, ConfluenceEvent)
            assert event.event_id.startswith('CONFLUENCE_')
            assert isinstance(event.confluence_type, ConfluenceType)
            assert isinstance(event.confluence_strength, ConfluenceStrength)
            assert isinstance(event.involved_nodes, list)
            assert 0.0 <= event.confluence_score <= 1.0
            assert isinstance(event.evidence, list)
            assert isinstance(event.timestamp, datetime)
            assert isinstance(event.duration, timedelta)
            assert isinstance(event.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, confluence_system):
        """Test LLM analysis generation"""
        prompt_template = "Test confluence_events prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        # Generate LLM analysis
        analysis = await confluence_system._generate_llm_analysis(prompt_template, data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'confluence_events' in analysis
        assert 'confluence_insights' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert isinstance(analysis['confluence_events'], list)
        assert len(analysis['confluence_events']) == 1
        assert analysis['confluence_events'][0]['confluence_type'] == 'signal_alignment'
        assert analysis['confluence_events'][0]['confluence_strength'] == 'strong'
        assert analysis['confluence_events'][0]['involved_signals'] == ['signal_1', 'signal_2']
        assert analysis['confluence_events'][0]['confluence_score'] == 0.8
        assert analysis['confluence_events'][0]['evidence'] == ['volume_confirmation', 'timing_sync']
        assert analysis['confluence_events'][0]['duration_minutes'] == 30
        assert analysis['confluence_insights'] == ['Strong signal alignment detected', 'Volume confirms confluence']
        assert analysis['uncertainty_flags'] == ['limited_sample_size']
    
    @pytest.mark.asyncio
    async def test_update_confluence_graph(self, confluence_system):
        """Test confluence graph updates"""
        # Create test confluence events
        confluence_events = [
            ConfluenceEvent(
                event_id='CONFLUENCE_1',
                confluence_type=ConfluenceType.SIGNAL_ALIGNMENT,
                confluence_strength=ConfluenceStrength.STRONG,
                involved_nodes=['signal_1', 'signal_2'],
                confluence_score=0.8,
                evidence=['volume_confirmation', 'timing_sync'],
                timestamp=datetime.now(timezone.utc),
                duration=timedelta(minutes=30),
                created_at=datetime.now(timezone.utc)
            ),
            ConfluenceEvent(
                event_id='CONFLUENCE_2',
                confluence_type=ConfluenceType.PATTERN_CONVERGENCE,
                confluence_strength=ConfluenceStrength.MODERATE,
                involved_nodes=['signal_2', 'signal_3'],
                confluence_score=0.6,
                evidence=['pattern_overlap'],
                timestamp=datetime.now(timezone.utc),
                duration=timedelta(minutes=45),
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Update confluence graph
        graph_updates = await confluence_system._update_confluence_graph(confluence_events)
        
        # Verify results
        assert isinstance(graph_updates, dict)
        assert 'nodes_added' in graph_updates
        assert 'nodes_updated' in graph_updates
        assert 'edges_added' in graph_updates
        assert 'edges_updated' in graph_updates
        assert 'nodes_removed' in graph_updates
        assert 'edges_removed' in graph_updates
        
        # Verify specific values
        assert graph_updates['nodes_added'] == 3  # Should add 3 nodes (signal_1, signal_2, signal_3)
        assert graph_updates['nodes_updated'] == 1  # signal_2 appears in both events, so it gets updated
        assert graph_updates['edges_added'] == 2  # Should add 2 edges (signal_1-signal_2, signal_2-signal_3)
        assert graph_updates['edges_updated'] == 0  # No existing edges to update
        assert graph_updates['nodes_removed'] == 0
        assert graph_updates['edges_removed'] == 0
        
        # Verify nodes were created
        assert len(confluence_system.nodes) == 3
        assert 'signal_1' in confluence_system.nodes
        assert 'signal_2' in confluence_system.nodes
        assert 'signal_3' in confluence_system.nodes
        
        # Verify edges were created
        assert len(confluence_system.edges) == 2
        assert 'signal_1_signal_2' in confluence_system.edges
        assert 'signal_2_signal_3' in confluence_system.edges
        
        # Verify node connections
        assert 'signal_2' in confluence_system.nodes['signal_1'].connections
        assert 'signal_1' in confluence_system.nodes['signal_2'].connections
        assert 'signal_3' in confluence_system.nodes['signal_2'].connections
        assert 'signal_2' in confluence_system.nodes['signal_3'].connections
    
    @pytest.mark.asyncio
    async def test_analyze_confluence_clusters(self, confluence_system):
        """Test confluence cluster analysis"""
        # Add some test confluence events
        confluence_system.confluence_events = [
            ConfluenceEvent(
                event_id='CONFLUENCE_1',
                confluence_type=ConfluenceType.SIGNAL_ALIGNMENT,
                confluence_strength=ConfluenceStrength.STRONG,
                involved_nodes=['signal_1', 'signal_2'],
                confluence_score=0.8,
                evidence=['volume_confirmation'],
                timestamp=datetime.now(timezone.utc),
                duration=timedelta(minutes=30),
                created_at=datetime.now(timezone.utc)
            ),
            ConfluenceEvent(
                event_id='CONFLUENCE_2',
                confluence_type=ConfluenceType.PATTERN_CONVERGENCE,
                confluence_strength=ConfluenceStrength.MODERATE,
                involved_nodes=['signal_2', 'signal_3'],
                confluence_score=0.6,
                evidence=['pattern_overlap'],
                timestamp=datetime.now(timezone.utc),
                duration=timedelta(minutes=45),
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Analyze confluence clusters
        cluster_analysis = await confluence_system._analyze_confluence_clusters()
        
        # Verify results
        assert isinstance(cluster_analysis, dict)
        assert 'clusters' in cluster_analysis
        assert 'insights' in cluster_analysis
        assert 'connections' in cluster_analysis
        
        # Verify specific values
        assert isinstance(cluster_analysis['clusters'], list)
        assert isinstance(cluster_analysis['insights'], list)
        assert isinstance(cluster_analysis['connections'], list)
        
        # Verify clusters were created
        assert len(confluence_system.confluence_clusters) > 0
        
        # Check cluster structure
        for cluster in confluence_system.confluence_clusters:
            assert isinstance(cluster, ConfluenceCluster)
            assert cluster.cluster_id.startswith('CLUSTER_')
            assert isinstance(cluster.cluster_type, str)
            assert isinstance(cluster.nodes, set)
            assert isinstance(cluster.edges, set)
            assert 0.0 <= cluster.cluster_score <= 1.0
            assert isinstance(cluster.dominant_confluence_type, ConfluenceType)
            assert isinstance(cluster.created_at, datetime)
            assert isinstance(cluster.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_analyze_confluence_clusters_insufficient_data(self, confluence_system):
        """Test confluence cluster analysis with insufficient data"""
        # Test with less than 2 events
        confluence_system.confluence_events = []
        
        cluster_analysis = await confluence_system._analyze_confluence_clusters()
        
        # Verify analysis
        assert isinstance(cluster_analysis, dict)
        assert cluster_analysis['clusters'] == []
        assert cluster_analysis['insights'] == []
        assert cluster_analysis['connections'] == []
    
    @pytest.mark.asyncio
    async def test_optimize_graph_structure(self, confluence_system):
        """Test graph structure optimization"""
        # Add nodes to exceed threshold
        for i in range(900):  # Add 900 nodes (90% of max size)
            node_id = f"node_{i}"
            node = ConfluenceNode(
                node_id=node_id,
                node_type=GraphNodeType.SIGNAL,
                node_data={'test': 'data'},
                connections=set(),
                confluence_score=0.5,
                last_updated=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            confluence_system.nodes[node_id] = node
        
        # Optimize graph structure
        optimization = await confluence_system._optimize_graph_structure()
        
        # Verify results
        assert isinstance(optimization, dict)
        assert 'actions' in optimization
        assert 'insights' in optimization
        assert 'improvements' in optimization
        
        # Verify specific values
        assert isinstance(optimization['actions'], list)
        assert isinstance(optimization['insights'], list)
        assert isinstance(optimization['improvements'], list)
    
    @pytest.mark.asyncio
    async def test_optimize_graph_structure_below_threshold(self, confluence_system):
        """Test graph structure optimization when below threshold"""
        # Add only a few nodes (below threshold)
        for i in range(5):
            node_id = f"node_{i}"
            node = ConfluenceNode(
                node_id=node_id,
                node_type=GraphNodeType.SIGNAL,
                node_data={'test': 'data'},
                connections=set(),
                confluence_score=0.5,
                last_updated=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            confluence_system.nodes[node_id] = node
        
        # Optimize graph structure
        optimization = await confluence_system._optimize_graph_structure()
        
        # Verify results
        assert isinstance(optimization, dict)
        assert optimization['actions'] == []
        assert optimization['insights'] == []
        assert optimization['improvements'] == []
    
    @pytest.mark.asyncio
    async def test_apply_optimization_action(self, confluence_system):
        """Test applying optimization actions"""
        # Add test node and edge
        node = ConfluenceNode(
            node_id='test_node',
            node_type=GraphNodeType.SIGNAL,
            node_data={'test': 'data'},
            connections={'other_node'},
            confluence_score=0.5,
            last_updated=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        confluence_system.nodes['test_node'] = node
        
        edge = ConfluenceEdge(
            edge_id='test_node_other_node',
            source_node='test_node',
            target_node='other_node',
            confluence_type=ConfluenceType.SIGNAL_ALIGNMENT,
            confluence_strength=ConfluenceStrength.MODERATE,
            weight=0.5,
            evidence=['test_evidence'],
            last_updated=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        confluence_system.edges['test_node_other_node'] = edge
        
        # Test remove node action
        action = {
            'action_type': 'remove_node',
            'target_id': 'test_node',
            'reason': 'test removal',
            'impact_score': 0.5
        }
        
        result = await confluence_system._apply_optimization_action(action)
        
        # Verify result
        assert result is True
        assert 'test_node' not in confluence_system.nodes
        assert 'test_node_other_node' not in confluence_system.edges
        
        # Test remove edge action
        edge = ConfluenceEdge(
            edge_id='test_edge_2',
            source_node='node_1',
            target_node='node_2',
            confluence_type=ConfluenceType.SIGNAL_ALIGNMENT,
            confluence_strength=ConfluenceStrength.MODERATE,
            weight=0.5,
            evidence=['test_evidence'],
            last_updated=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        confluence_system.edges['test_edge_2'] = edge
        
        action = {
            'action_type': 'remove_edge',
            'target_id': 'test_edge_2',
            'reason': 'test edge removal',
            'impact_score': 0.3
        }
        
        result = await confluence_system._apply_optimization_action(action)
        
        # Verify result
        assert result is True
        assert 'test_edge_2' not in confluence_system.edges
    
    @pytest.mark.asyncio
    async def test_publish_confluence_results(self, confluence_system, mock_supabase_manager):
        """Test publishing confluence results"""
        results = {
            'confluence_events': [{'event_id': 'CONFLUENCE_1'}],
            'graph_updates': {'nodes_added': 3, 'edges_added': 2},
            'cluster_analysis': {'clusters': []},
            'graph_optimization': {'actions': []},
            'confluence_timestamp': datetime.now(timezone.utc),
            'confluence_errors': []
        }
        
        await confluence_system._publish_confluence_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_confluence'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'confluence_graph_system'
        assert call_args['strategic_meta_type'] == 'confluence_analysis'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
