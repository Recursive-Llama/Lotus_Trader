"""
CIL Confluence Graph System - Missing Piece 2
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class ConfluenceType(Enum):
    """Types of confluence events"""
    SIGNAL_ALIGNMENT = "signal_alignment"
    PATTERN_CONVERGENCE = "pattern_convergence"
    TIMING_SYNCHRONIZATION = "timing_synchronization"
    VOLUME_CONFIRMATION = "volume_confirmation"
    REGIME_CONFLUENCE = "regime_confluence"
    CROSS_ASSET_CONFLUENCE = "cross_asset_confluence"


class ConfluenceStrength(Enum):
    """Strength of confluence events"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    OVERWHELMING = "overwhelming"


class GraphNodeType(Enum):
    """Types of nodes in the confluence graph"""
    SIGNAL = "signal"
    PATTERN = "pattern"
    AGENT = "agent"
    TIMEFRAME = "timeframe"
    ASSET = "asset"
    REGIME = "regime"


@dataclass
class ConfluenceNode:
    """A node in the confluence graph"""
    node_id: str
    node_type: GraphNodeType
    node_data: Dict[str, Any]
    connections: Set[str]
    confluence_score: float
    last_updated: datetime
    created_at: datetime


@dataclass
class ConfluenceEdge:
    """An edge in the confluence graph"""
    edge_id: str
    source_node: str
    target_node: str
    confluence_type: ConfluenceType
    confluence_strength: ConfluenceStrength
    weight: float
    evidence: List[str]
    last_updated: datetime
    created_at: datetime


@dataclass
class ConfluenceEvent:
    """A confluence event between multiple signals/patterns"""
    event_id: str
    confluence_type: ConfluenceType
    confluence_strength: ConfluenceStrength
    involved_nodes: List[str]
    confluence_score: float
    evidence: List[str]
    timestamp: datetime
    duration: Optional[timedelta]
    created_at: datetime


@dataclass
class ConfluenceCluster:
    """A cluster of related confluence events"""
    cluster_id: str
    cluster_type: str
    nodes: Set[str]
    edges: Set[str]
    cluster_score: float
    dominant_confluence_type: ConfluenceType
    created_at: datetime
    updated_at: datetime


class ConfluenceGraphSystem:
    """CIL Confluence Graph System - Tracks confluence between signals and patterns"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.confluence_threshold = 0.7
        self.cluster_threshold = 0.8
        self.graph_update_interval_minutes = 5
        self.max_graph_size = 1000
        self.edge_decay_factor = 0.95
        
        # Graph state
        self.nodes: Dict[str, ConfluenceNode] = {}
        self.edges: Dict[str, ConfluenceEdge] = {}
        self.confluence_events: List[ConfluenceEvent] = []
        self.confluence_clusters: List[ConfluenceCluster] = []
        
        # LLM prompt templates
        self.confluence_analysis_prompt = self._load_confluence_analysis_prompt()
        self.cluster_analysis_prompt = self._load_cluster_analysis_prompt()
        self.graph_optimization_prompt = self._load_graph_optimization_prompt()
    
    def _load_confluence_analysis_prompt(self) -> str:
        """Load confluence analysis prompt template"""
        return """
        Analyze the following signals and patterns for confluence events.
        
        Signals/Patterns:
        {signals_patterns}
        
        Context:
        - Timeframe: {timeframe}
        - Regime: {regime}
        - Session: {session}
        - Cross-asset state: {cross_asset_state}
        
        Identify:
        1. Confluence events between signals/patterns
        2. Type of confluence (signal alignment, pattern convergence, timing sync, etc.)
        3. Strength of confluence (weak/moderate/strong/overwhelming)
        4. Evidence supporting the confluence
        5. Confluence score (0.0-1.0)
        
        Respond in JSON format:
        {{
            "confluence_events": [
                {{
                    "confluence_type": "signal_alignment|pattern_convergence|timing_synchronization|volume_confirmation|regime_confluence|cross_asset_confluence",
                    "confluence_strength": "weak|moderate|strong|overwhelming",
                    "involved_signals": ["list of signal IDs"],
                    "confluence_score": 0.0-1.0,
                    "evidence": ["list of evidence"],
                    "duration_minutes": 30
                }}
            ],
            "confluence_insights": ["list of insights"],
            "uncertainty_flags": ["any uncertainties"]
        }}
        """
    
    def _load_cluster_analysis_prompt(self) -> str:
        """Load cluster analysis prompt template"""
        return """
        Analyze the following confluence events and identify clusters.
        
        Confluence Events:
        {confluence_events}
        
        Graph Structure:
        - Nodes: {node_count}
        - Edges: {edge_count}
        - Clusters: {cluster_count}
        
        Identify:
        1. Clusters of related confluence events
        2. Dominant confluence types within clusters
        3. Cluster strength and coherence
        4. Cross-cluster connections
        5. Cluster evolution patterns
        
        Respond in JSON format:
        {{
            "clusters": [
                {{
                    "cluster_type": "signal_cluster|pattern_cluster|regime_cluster|cross_asset_cluster",
                    "nodes": ["list of node IDs"],
                    "edges": ["list of edge IDs"],
                    "cluster_score": 0.0-1.0,
                    "dominant_confluence_type": "confluence type",
                    "coherence_score": 0.0-1.0
                }}
            ],
            "cluster_insights": ["list of insights"],
            "cross_cluster_connections": ["list of connections"]
        }}
        """
    
    def _load_graph_optimization_prompt(self) -> str:
        """Load graph optimization prompt template"""
        return """
        Optimize the confluence graph structure for better performance and insights.
        
        Current Graph:
        - Nodes: {node_count}
        - Edges: {edge_count}
        - Clusters: {cluster_count}
        - Max size: {max_size}
        
        Optimization Goals:
        1. Remove low-value nodes and edges
        2. Consolidate redundant connections
        3. Identify critical confluence paths
        4. Optimize cluster structure
        5. Maintain graph coherence
        
        Respond in JSON format:
        {{
            "optimization_actions": [
                {{
                    "action_type": "remove_node|remove_edge|merge_nodes|split_cluster|consolidate_edges",
                    "target_id": "node/edge/cluster ID",
                    "reason": "optimization reason",
                    "impact_score": 0.0-1.0
                }}
            ],
            "optimization_insights": ["list of insights"],
            "performance_improvements": ["list of improvements"]
        }}
        """
    
    async def process_confluence_analysis(self, recent_strands: List[Dict[str, Any]],
                                        global_synthesis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process confluence analysis and update graph"""
        try:
            # Extract signals and patterns from recent strands
            signals_patterns = await self._extract_signals_patterns(recent_strands)
            
            # Analyze confluence events
            confluence_events = await self._analyze_confluence_events(signals_patterns, global_synthesis_results)
            
            # Update confluence graph
            graph_updates = await self._update_confluence_graph(confluence_events)
            
            # Analyze confluence clusters
            cluster_analysis = await self._analyze_confluence_clusters()
            
            # Optimize graph structure
            graph_optimization = await self._optimize_graph_structure()
            
            # Compile results
            results = {
                'confluence_events': confluence_events,
                'graph_updates': graph_updates,
                'cluster_analysis': cluster_analysis,
                'graph_optimization': graph_optimization,
                'confluence_timestamp': datetime.now(timezone.utc),
                'confluence_errors': []
            }
            
            # Publish results
            await self._publish_confluence_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing confluence analysis: {e}")
            return {
                'confluence_events': [],
                'graph_updates': [],
                'cluster_analysis': [],
                'graph_optimization': [],
                'confluence_timestamp': datetime.now(timezone.utc),
                'confluence_errors': [str(e)]
            }
    
    async def _extract_signals_patterns(self, recent_strands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract signals and patterns from recent strands"""
        signals_patterns = []
        
        for strand in recent_strands:
            # Extract signal/pattern data
            signal_data = {
                'strand_id': strand.get('id', ''),
                'agent_id': strand.get('agent_id', ''),
                'pattern_family': strand.get('pattern_family', ''),
                'signal_type': strand.get('signal_type', ''),
                'timeframe': strand.get('timeframe', ''),
                'symbol': strand.get('symbol', ''),
                'regime': strand.get('regime', ''),
                'session_bucket': strand.get('session_bucket', ''),
                'sig_confidence': strand.get('sig_confidence', 0.0),
                'sig_sigma': strand.get('sig_sigma', 0.0),
                'created_at': strand.get('created_at', ''),
                'content': strand.get('content', '')
            }
            signals_patterns.append(signal_data)
        
        return signals_patterns
    
    async def _analyze_confluence_events(self, signals_patterns: List[Dict[str, Any]],
                                       global_synthesis_results: Dict[str, Any]) -> List[ConfluenceEvent]:
        """Analyze confluence events between signals and patterns"""
        confluence_events = []
        
        # Group signals by timeframe and symbol for confluence analysis
        signal_groups = await self._group_signals_for_confluence(signals_patterns)
        
        for group_key, group_signals in signal_groups.items():
            if len(group_signals) < 2:
                continue  # Need at least 2 signals for confluence
            
            # Analyze confluence within this group
            group_confluence = await self._analyze_group_confluence(group_signals, global_synthesis_results)
            confluence_events.extend(group_confluence)
        
        return confluence_events
    
    async def _group_signals_for_confluence(self, signals_patterns: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group signals for confluence analysis"""
        groups = {}
        
        for signal in signals_patterns:
            # Group by timeframe and symbol
            group_key = f"{signal['timeframe']}_{signal['symbol']}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(signal)
        
        return groups
    
    async def _analyze_group_confluence(self, group_signals: List[Dict[str, Any]],
                                      global_synthesis_results: Dict[str, Any]) -> List[ConfluenceEvent]:
        """Analyze confluence within a group of signals"""
        confluence_events = []
        
        # Prepare data for LLM analysis
        analysis_data = {
            'signals_patterns': group_signals,
            'timeframe': group_signals[0]['timeframe'],
            'regime': group_signals[0]['regime'],
            'session': group_signals[0]['session_bucket'],
            'cross_asset_state': global_synthesis_results.get('cross_asset_state', {})
        }
        
        # Generate confluence analysis using LLM
        analysis = await self._generate_llm_analysis(
            self.confluence_analysis_prompt, analysis_data
        )
        
        if not analysis:
            return confluence_events
        
        # Create confluence events from analysis
        for event_data in analysis.get('confluence_events', []):
            confluence_event = ConfluenceEvent(
                event_id=f"CONFLUENCE_{int(datetime.now().timestamp())}",
                confluence_type=ConfluenceType(event_data.get('confluence_type', 'signal_alignment')),
                confluence_strength=ConfluenceStrength(event_data.get('confluence_strength', 'weak')),
                involved_nodes=event_data.get('involved_signals', []),
                confluence_score=event_data.get('confluence_score', 0.5),
                evidence=event_data.get('evidence', []),
                timestamp=datetime.now(timezone.utc),
                duration=timedelta(minutes=event_data.get('duration_minutes', 30)),
                created_at=datetime.now(timezone.utc)
            )
            confluence_events.append(confluence_event)
        
        return confluence_events
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            if 'confluence_events' in formatted_prompt:
                response = {
                    "confluence_events": [
                        {
                            "confluence_type": "signal_alignment",
                            "confluence_strength": "strong",
                            "involved_signals": ["signal_1", "signal_2"],
                            "confluence_score": 0.8,
                            "evidence": ["volume_confirmation", "timing_sync"],
                            "duration_minutes": 30
                        }
                    ],
                    "confluence_insights": ["Strong signal alignment detected", "Volume confirms confluence"],
                    "uncertainty_flags": ["limited_sample_size"]
                }
            elif 'clusters' in formatted_prompt:
                response = {
                    "clusters": [
                        {
                            "cluster_type": "signal_cluster",
                            "nodes": ["signal_1", "signal_2"],
                            "edges": ["signal_1_signal_2"],
                            "cluster_score": 0.8,
                            "dominant_confluence_type": "signal_alignment",
                            "coherence_score": 0.7
                        }
                    ],
                    "cluster_insights": ["Strong signal cluster detected"],
                    "cross_cluster_connections": []
                }
            else:
                response = {
                    "optimization_actions": [
                        {
                            "action_type": "remove_node",
                            "target_id": "test_node",
                            "reason": "low_value",
                            "impact_score": 0.5
                        }
                    ],
                    "optimization_insights": ["Graph optimization applied"],
                    "performance_improvements": ["Reduced graph size"]
                }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    async def _update_confluence_graph(self, confluence_events: List[ConfluenceEvent]) -> Dict[str, Any]:
        """Update confluence graph with new events"""
        graph_updates = {
            'nodes_added': 0,
            'nodes_updated': 0,
            'edges_added': 0,
            'edges_updated': 0,
            'nodes_removed': 0,
            'edges_removed': 0
        }
        
        for event in confluence_events:
            # Update nodes for involved signals
            for node_id in event.involved_nodes:
                if node_id in self.nodes:
                    # Update existing node
                    self.nodes[node_id].confluence_score = max(
                        self.nodes[node_id].confluence_score, event.confluence_score
                    )
                    self.nodes[node_id].last_updated = datetime.now(timezone.utc)
                    graph_updates['nodes_updated'] += 1
                else:
                    # Create new node
                    node = ConfluenceNode(
                        node_id=node_id,
                        node_type=GraphNodeType.SIGNAL,
                        node_data={'confluence_event_id': event.event_id},
                        connections=set(),
                        confluence_score=event.confluence_score,
                        last_updated=datetime.now(timezone.utc),
                        created_at=datetime.now(timezone.utc)
                    )
                    self.nodes[node_id] = node
                    graph_updates['nodes_added'] += 1
            
            # Create edges between involved nodes
            for i, source_node in enumerate(event.involved_nodes):
                for target_node in event.involved_nodes[i+1:]:
                    edge_id = f"{source_node}_{target_node}"
                    
                    if edge_id in self.edges:
                        # Update existing edge
                        self.edges[edge_id].weight = max(
                            self.edges[edge_id].weight, event.confluence_score
                        )
                        self.edges[edge_id].last_updated = datetime.now(timezone.utc)
                        graph_updates['edges_updated'] += 1
                    else:
                        # Create new edge
                        edge = ConfluenceEdge(
                            edge_id=edge_id,
                            source_node=source_node,
                            target_node=target_node,
                            confluence_type=event.confluence_type,
                            confluence_strength=event.confluence_strength,
                            weight=event.confluence_score,
                            evidence=event.evidence,
                            last_updated=datetime.now(timezone.utc),
                            created_at=datetime.now(timezone.utc)
                        )
                        self.edges[edge_id] = edge
                        graph_updates['edges_added'] += 1
                        
                        # Update node connections
                        if source_node in self.nodes:
                            self.nodes[source_node].connections.add(target_node)
                        if target_node in self.nodes:
                            self.nodes[target_node].connections.add(source_node)
        
        # Add event to confluence events list
        self.confluence_events.extend(confluence_events)
        
        return graph_updates
    
    async def _analyze_confluence_clusters(self) -> Dict[str, Any]:
        """Analyze confluence clusters in the graph"""
        try:
            if len(self.confluence_events) < 2:
                return {'clusters': [], 'insights': [], 'connections': []}
            
            # Prepare data for cluster analysis
            analysis_data = {
                'confluence_events': [event.__dict__ for event in self.confluence_events],
                'node_count': len(self.nodes),
                'edge_count': len(self.edges),
                'cluster_count': len(self.confluence_clusters)
            }
            
            # Generate cluster analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.cluster_analysis_prompt, analysis_data
            )
            
            if not analysis:
                return {'clusters': [], 'insights': [], 'connections': []}
            
            # Update confluence clusters
            new_clusters = []
            for cluster_data in analysis.get('clusters', []):
                cluster = ConfluenceCluster(
                    cluster_id=f"CLUSTER_{int(datetime.now().timestamp())}",
                    cluster_type=cluster_data.get('cluster_type', 'signal_cluster'),
                    nodes=set(cluster_data.get('nodes', [])),
                    edges=set(cluster_data.get('edges', [])),
                    cluster_score=cluster_data.get('cluster_score', 0.5),
                    dominant_confluence_type=ConfluenceType(cluster_data.get('dominant_confluence_type', 'signal_alignment')),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                new_clusters.append(cluster)
            
            self.confluence_clusters = new_clusters
            
            return {
                'clusters': [cluster.__dict__ for cluster in new_clusters],
                'insights': analysis.get('cluster_insights', []),
                'connections': analysis.get('cross_cluster_connections', [])
            }
            
        except Exception as e:
            print(f"Error analyzing confluence clusters: {e}")
            return {'clusters': [], 'insights': [], 'connections': []}
    
    async def _optimize_graph_structure(self) -> Dict[str, Any]:
        """Optimize graph structure for better performance"""
        try:
            # Check if optimization is needed
            if len(self.nodes) < self.max_graph_size * 0.8:
                return {'actions': [], 'insights': [], 'improvements': []}
            
            # Prepare data for optimization analysis
            analysis_data = {
                'node_count': len(self.nodes),
                'edge_count': len(self.edges),
                'cluster_count': len(self.confluence_clusters),
                'max_size': self.max_graph_size
            }
            
            # Generate optimization analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.graph_optimization_prompt, analysis_data
            )
            
            if not analysis:
                return {'actions': [], 'insights': [], 'improvements': []}
            
            # Apply optimization actions
            optimization_actions = analysis.get('optimization_actions', [])
            applied_actions = []
            
            for action in optimization_actions:
                if await self._apply_optimization_action(action):
                    applied_actions.append(action)
            
            return {
                'actions': applied_actions,
                'insights': analysis.get('optimization_insights', []),
                'improvements': analysis.get('performance_improvements', [])
            }
            
        except Exception as e:
            print(f"Error optimizing graph structure: {e}")
            return {'actions': [], 'insights': [], 'improvements': []}
    
    async def _apply_optimization_action(self, action: Dict[str, Any]) -> bool:
        """Apply a single optimization action"""
        try:
            action_type = action.get('action_type', '')
            target_id = action.get('target_id', '')
            
            if action_type == 'remove_node' and target_id in self.nodes:
                # Remove node and its edges
                node = self.nodes[target_id]
                for connection in node.connections:
                    edge_id = f"{target_id}_{connection}"
                    if edge_id in self.edges:
                        del self.edges[edge_id]
                    edge_id = f"{connection}_{target_id}"
                    if edge_id in self.edges:
                        del self.edges[edge_id]
                del self.nodes[target_id]
                return True
            
            elif action_type == 'remove_edge' and target_id in self.edges:
                # Remove edge
                edge = self.edges[target_id]
                if edge.source_node in self.nodes:
                    self.nodes[edge.source_node].connections.discard(edge.target_node)
                if edge.target_node in self.nodes:
                    self.nodes[edge.target_node].connections.discard(edge.source_node)
                del self.edges[target_id]
                return True
            
            return False
            
        except Exception as e:
            print(f"Error applying optimization action: {e}")
            return False
    
    async def _publish_confluence_results(self, results: Dict[str, Any]):
        """Publish confluence results as CIL strand"""
        try:
            # Create CIL confluence strand
            cil_strand = {
                'id': f"cil_confluence_{int(datetime.now().timestamp())}",
                'kind': 'cil_confluence',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:confluence_graph_system:confluence_analysis'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'confluence_graph_system',
                'strategic_meta_type': 'confluence_analysis',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing confluence results: {e}")


# Example usage and testing
async def main():
    """Example usage of ConfluenceGraphSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create confluence graph system
    confluence_system = ConfluenceGraphSystem(supabase_manager, llm_client)
    
    # Mock recent strands
    recent_strands = [
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
        }
    ]
    
    global_synthesis_results = {
        'cross_asset_state': {'BTC': 'bullish', 'ETH': 'neutral'}
    }
    
    # Process confluence analysis
    results = await confluence_system.process_confluence_analysis(recent_strands, global_synthesis_results)
    
    print("Confluence Analysis Results:")
    print(f"Confluence Events: {len(results['confluence_events'])}")
    print(f"Graph Updates: {results['graph_updates']}")
    print(f"Cluster Analysis: {len(results['cluster_analysis'])}")
    print(f"Graph Optimization: {len(results['graph_optimization'])}")


if __name__ == "__main__":
    asyncio.run(main())
