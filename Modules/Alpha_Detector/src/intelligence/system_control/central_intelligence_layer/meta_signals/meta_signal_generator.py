"""
Meta-Signal Generator - CIL Signal Generation
Generates higher-order meta-signals from cross-agent patterns and timing
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


@dataclass
class MetaSignal:
    """Meta-signal data structure"""
    signal_id: str
    signal_type: str  # 'confluence_event', 'lead_lag_predict', 'transfer_hit'
    source_agents: List[str]
    target_agents: List[str]
    confidence: float
    evidence: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None


class MetaSignalGenerator:
    """
    Generates meta-signals from cross-agent patterns and timing
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.meta_signal_types = [
            'confluence_event',
            'lead_lag_predict', 
            'transfer_hit',
            'strategic_confluence',
            'experiment_directive',
            'doctrine_update'
        ]
    
    async def generate_meta_signals(self, time_window_minutes: int = 60) -> List[MetaSignal]:
        """
        Generate meta-signals from recent agent activity
        
        Args:
            time_window_minutes: Time window to analyze for patterns
            
        Returns:
            List of generated meta-signals
        """
        try:
            # Get recent strands from all agents
            recent_strands = await self._get_recent_strands(time_window_minutes)
            
            if not recent_strands:
                return []
            
            # Generate different types of meta-signals
            meta_signals = []
            
            # 1. Confluence Events (A∧B within Δt)
            confluence_signals = await self._detect_confluence_events(recent_strands)
            meta_signals.extend(confluence_signals)
            
            # 2. Lead-Lag Predictions (A→B motifs)
            lead_lag_signals = await self._detect_lead_lag_patterns(recent_strands)
            meta_signals.extend(lead_lag_signals)
            
            # 3. Transfer Hits (cross-asset/session generalization)
            transfer_signals = await self._detect_transfer_hits(recent_strands)
            meta_signals.extend(transfer_signals)
            
            # 4. Strategic Confluence (cross-team patterns)
            strategic_signals = await self._detect_strategic_confluence(recent_strands)
            meta_signals.extend(strategic_signals)
            
            # Publish meta-signals to database
            for signal in meta_signals:
                await self._publish_meta_signal(signal)
            
            return meta_signals
            
        except Exception as e:
            print(f"Error generating meta-signals: {e}")
            return []
    
    async def _get_recent_strands(self, time_window_minutes: int) -> List[Dict[str, Any]]:
        """Get recent strands from all agents"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            # Query recent strands with agent information
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= %s 
                AND tags IS NOT NULL
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time.isoformat()])
            return result if result else []
            
        except Exception as e:
            print(f"Error getting recent strands: {e}")
            return []
    
    async def _detect_confluence_events(self, strands: List[Dict[str, Any]]) -> List[MetaSignal]:
        """
        Detect confluence events: multiple agents detecting similar patterns within time window
        """
        confluence_signals = []
        
        try:
            # Group strands by time windows (5-minute buckets)
            time_buckets = self._group_strands_by_time_buckets(strands, bucket_minutes=5)
            
            for bucket_time, bucket_strands in time_buckets.items():
                if len(bucket_strands) < 2:
                    continue
                
                # Find patterns across different agents
                agent_patterns = self._extract_agent_patterns(bucket_strands)
                
                # Look for confluence (similar patterns from different agents)
                confluence_candidates = self._find_confluence_candidates(agent_patterns)
                
                for confluence in confluence_candidates:
                    signal = MetaSignal(
                        signal_id=f"confluence_{int(bucket_time.timestamp())}_{len(confluence_signals)}",
                        signal_type='confluence_event',
                        source_agents=confluence['source_agents'],
                        target_agents=confluence['target_agents'],
                        confidence=confluence['confidence'],
                        evidence=confluence['evidence'],
                        created_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                    )
                    confluence_signals.append(signal)
            
            return confluence_signals
            
        except Exception as e:
            print(f"Error detecting confluence events: {e}")
            return []
    
    async def _detect_lead_lag_patterns(self, strands: List[Dict[str, Any]]) -> List[MetaSignal]:
        """
        Detect lead-lag patterns: one agent consistently firing before another
        """
        lead_lag_signals = []
        
        try:
            # Sort strands by time
            sorted_strands = sorted(strands, key=lambda x: x.get('created_at', ''))
            
            # Look for lead-lag patterns in agent sequences
            agent_sequences = self._build_agent_sequences(sorted_strands)
            
            # Find consistent lead-lag relationships
            lead_lag_relationships = self._find_lead_lag_relationships(agent_sequences)
            
            for relationship in lead_lag_relationships:
                signal = MetaSignal(
                    signal_id=f"lead_lag_{int(datetime.now().timestamp())}_{len(lead_lag_signals)}",
                    signal_type='lead_lag_predict',
                    source_agents=[relationship['lead_agent']],
                    target_agents=[relationship['lag_agent']],
                    confidence=relationship['confidence'],
                    evidence=relationship['evidence'],
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=12)
                )
                lead_lag_signals.append(signal)
            
            return lead_lag_signals
            
        except Exception as e:
            print(f"Error detecting lead-lag patterns: {e}")
            return []
    
    async def _detect_transfer_hits(self, strands: List[Dict[str, Any]]) -> List[MetaSignal]:
        """
        Detect transfer hits: patterns generalizing across assets/sessions
        """
        transfer_signals = []
        
        try:
            # Group strands by pattern similarity
            pattern_groups = self._group_strands_by_pattern_similarity(strands)
            
            for pattern_group in pattern_groups:
                if len(pattern_group) < 2:
                    continue
                
                # Check if pattern appears across different contexts
                transfer_candidates = self._find_transfer_candidates(pattern_group)
                
                for transfer in transfer_candidates:
                    signal = MetaSignal(
                        signal_id=f"transfer_{int(datetime.now().timestamp())}_{len(transfer_signals)}",
                        signal_type='transfer_hit',
                        source_agents=transfer['source_agents'],
                        target_agents=transfer['target_agents'],
                        confidence=transfer['confidence'],
                        evidence=transfer['evidence'],
                        created_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=6)
                    )
                    transfer_signals.append(signal)
            
            return transfer_signals
            
        except Exception as e:
            print(f"Error detecting transfer hits: {e}")
            return []
    
    async def _detect_strategic_confluence(self, strands: List[Dict[str, Any]]) -> List[MetaSignal]:
        """
        Detect strategic confluence: cross-team patterns that suggest strategic opportunities
        """
        strategic_signals = []
        
        try:
            # Look for patterns across different intelligence teams
            team_patterns = self._extract_team_patterns(strands)
            
            # Find strategic confluence opportunities
            strategic_opportunities = self._find_strategic_opportunities(team_patterns)
            
            for opportunity in strategic_opportunities:
                signal = MetaSignal(
                    signal_id=f"strategic_{int(datetime.now().timestamp())}_{len(strategic_signals)}",
                    signal_type='strategic_confluence',
                    source_agents=opportunity['source_teams'],
                    target_agents=opportunity['target_teams'],
                    confidence=opportunity['confidence'],
                    evidence=opportunity['evidence'],
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
                )
                strategic_signals.append(signal)
            
            return strategic_signals
            
        except Exception as e:
            print(f"Error detecting strategic confluence: {e}")
            return []
    
    def _group_strands_by_time_buckets(self, strands: List[Dict[str, Any]], bucket_minutes: int = 5) -> Dict[datetime, List[Dict[str, Any]]]:
        """Group strands into time buckets"""
        buckets = {}
        
        for strand in strands:
            try:
                created_at = datetime.fromisoformat(strand.get('created_at', '').replace('Z', '+00:00'))
                bucket_time = created_at.replace(minute=(created_at.minute // bucket_minutes) * bucket_minutes, second=0, microsecond=0)
                
                if bucket_time not in buckets:
                    buckets[bucket_time] = []
                buckets[bucket_time].append(strand)
                
            except Exception as e:
                print(f"Error parsing strand timestamp: {e}")
                continue
        
        return buckets
    
    def _extract_agent_patterns(self, strands: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract patterns by agent"""
        agent_patterns = {}
        
        for strand in strands:
            # Extract agent from tags
            agent = self._extract_agent_from_tags(strand.get('tags', []))
            if agent:
                if agent not in agent_patterns:
                    agent_patterns[agent] = []
                agent_patterns[agent].append(strand)
        
        return agent_patterns
    
    def _extract_agent_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract agent name from tags"""
        for tag in tags:
            if 'agent:' in tag:
                parts = tag.split(':')
                if len(parts) >= 2:
                    return parts[1]  # Return agent name
        return None
    
    def _find_confluence_candidates(self, agent_patterns: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find confluence candidates from agent patterns"""
        confluence_candidates = []
        
        # Simple confluence detection: if multiple agents have similar patterns
        agents = list(agent_patterns.keys())
        
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                agent1, agent2 = agents[i], agents[j]
                patterns1, patterns2 = agent_patterns[agent1], agent_patterns[agent2]
                
                # Check for pattern similarity
                similarity = self._calculate_pattern_similarity(patterns1, patterns2)
                
                if similarity > 0.6:  # Threshold for confluence
                    confluence_candidates.append({
                        'source_agents': [agent1, agent2],
                        'target_agents': ['all_teams'],
                        'confidence': similarity,
                        'evidence': {
                            'agent1_patterns': len(patterns1),
                            'agent2_patterns': len(patterns2),
                            'similarity_score': similarity,
                            'pattern_types': self._extract_pattern_types(patterns1 + patterns2)
                        }
                    })
        
        return confluence_candidates
    
    def _calculate_pattern_similarity(self, patterns1: List[Dict[str, Any]], patterns2: List[Dict[str, Any]]) -> float:
        """Calculate similarity between two sets of patterns"""
        # Simple similarity based on common symbols, timeframes, and regimes
        if not patterns1 or not patterns2:
            return 0.0
        
        # Extract features from patterns
        features1 = self._extract_pattern_features(patterns1)
        features2 = self._extract_pattern_features(patterns2)
        
        # Calculate Jaccard similarity
        intersection = len(features1.intersection(features2))
        union = len(features1.union(features2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_pattern_features(self, patterns: List[Dict[str, Any]]) -> set:
        """Extract features from patterns for similarity calculation"""
        features = set()
        
        for pattern in patterns:
            # Add symbol, timeframe, regime, session as features
            features.add(f"symbol:{pattern.get('symbol', 'unknown')}")
            features.add(f"timeframe:{pattern.get('timeframe', 'unknown')}")
            features.add(f"regime:{pattern.get('regime', 'unknown')}")
            features.add(f"session:{pattern.get('session_bucket', 'unknown')}")
            
            # Add pattern type from tags
            tags = pattern.get('tags', [])
            for tag in tags:
                if ':' in tag:
                    features.add(f"tag:{tag}")
        
        return features
    
    def _extract_pattern_types(self, patterns: List[Dict[str, Any]]) -> List[str]:
        """Extract pattern types from patterns"""
        pattern_types = []
        
        for pattern in patterns:
            tags = pattern.get('tags', [])
            for tag in tags:
                if ':' in tag and tag not in pattern_types:
                    pattern_types.append(tag)
        
        return pattern_types
    
    def _build_agent_sequences(self, strands: List[Dict[str, Any]]) -> Dict[str, List[datetime]]:
        """Build sequences of agent activity times"""
        agent_sequences = {}
        
        for strand in strands:
            try:
                agent = self._extract_agent_from_tags(strand.get('tags', []))
                if agent:
                    created_at = datetime.fromisoformat(strand.get('created_at', '').replace('Z', '+00:00'))
                    
                    if agent not in agent_sequences:
                        agent_sequences[agent] = []
                    agent_sequences[agent].append(created_at)
                    
            except Exception as e:
                print(f"Error building agent sequence: {e}")
                continue
        
        # Sort sequences by time
        for agent in agent_sequences:
            agent_sequences[agent].sort()
        
        return agent_sequences
    
    def _find_lead_lag_relationships(self, agent_sequences: Dict[str, List[datetime]]) -> List[Dict[str, Any]]:
        """Find lead-lag relationships between agents"""
        relationships = []
        
        agents = list(agent_sequences.keys())
        
        for i in range(len(agents)):
            for j in range(len(agents)):
                if i == j:
                    continue
                
                agent1, agent2 = agents[i], agents[j]
                seq1, seq2 = agent_sequences[agent1], agent_sequences[agent2]
                
                # Check if agent1 consistently leads agent2
                lead_count = 0
                total_pairs = 0
                
                for time1 in seq1:
                    for time2 in seq2:
                        time_diff = (time2 - time1).total_seconds()
                        if 0 < time_diff < 300:  # Within 5 minutes
                            total_pairs += 1
                            if time1 < time2:
                                lead_count += 1
                
                if total_pairs > 0:
                    lead_ratio = lead_count / total_pairs
                    if lead_ratio > 0.7:  # Threshold for lead-lag relationship
                        relationships.append({
                            'lead_agent': agent1,
                            'lag_agent': agent2,
                            'confidence': lead_ratio,
                            'evidence': {
                                'total_pairs': total_pairs,
                                'lead_count': lead_count,
                                'lead_ratio': lead_ratio
                            }
                        })
        
        return relationships
    
    def _group_strands_by_pattern_similarity(self, strands: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group strands by pattern similarity"""
        # Simple grouping by symbol and timeframe for now
        groups = {}
        
        for strand in strands:
            key = f"{strand.get('symbol', 'unknown')}_{strand.get('timeframe', 'unknown')}"
            if key not in groups:
                groups[key] = []
            groups[key].append(strand)
        
        return list(groups.values())
    
    def _find_transfer_candidates(self, pattern_group: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find transfer candidates from pattern group"""
        transfer_candidates = []
        
        # Check if patterns appear across different contexts (sessions, regimes)
        contexts = set()
        agents = set()
        
        for strand in pattern_group:
            contexts.add(f"{strand.get('session_bucket', 'unknown')}_{strand.get('regime', 'unknown')}")
            agent = self._extract_agent_from_tags(strand.get('tags', []))
            if agent:
                agents.add(agent)
        
        # If pattern appears in multiple contexts, it's a transfer candidate
        if len(contexts) > 1 and len(agents) > 0:
            transfer_candidates.append({
                'source_agents': list(agents),
                'target_agents': ['all_teams'],
                'confidence': min(len(contexts) / 3.0, 1.0),  # Cap at 1.0
                'evidence': {
                    'contexts': list(contexts),
                    'agents': list(agents),
                    'pattern_count': len(pattern_group)
                }
            })
        
        return transfer_candidates
    
    def _extract_team_patterns(self, strands: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract patterns by intelligence team"""
        team_patterns = {}
        
        for strand in strands:
            # Extract team from agent tags
            team = self._extract_team_from_tags(strand.get('tags', []))
            if team:
                if team not in team_patterns:
                    team_patterns[team] = []
                team_patterns[team].append(strand)
        
        return team_patterns
    
    def _extract_team_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract team name from tags"""
        for tag in tags:
            if 'agent:' in tag:
                parts = tag.split(':')
                if len(parts) >= 2:
                    # Map agent to team
                    agent = parts[1]
                    if 'raw_data' in agent:
                        return 'raw_data_intelligence'
                    elif 'indicator' in agent:
                        return 'indicator_intelligence'
                    elif 'pattern' in agent:
                        return 'pattern_intelligence'
                    elif 'system_control' in agent:
                        return 'system_control'
                    elif 'central_intelligence' in agent:
                        return 'central_intelligence_layer'
        return None
    
    def _find_strategic_opportunities(self, team_patterns: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find strategic opportunities from team patterns"""
        opportunities = []
        
        teams = list(team_patterns.keys())
        
        # Look for patterns that could benefit from cross-team coordination
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                team1, team2 = teams[i], teams[j]
                patterns1, patterns2 = team_patterns[team1], team_patterns[team2]
                
                # Check for complementary patterns
                complementarity = self._calculate_team_complementarity(patterns1, patterns2)
                
                if complementarity > 0.5:  # Threshold for strategic opportunity
                    opportunities.append({
                        'source_teams': [team1, team2],
                        'target_teams': ['all_teams'],
                        'confidence': complementarity,
                        'evidence': {
                            'team1_patterns': len(patterns1),
                            'team2_patterns': len(patterns2),
                            'complementarity_score': complementarity,
                            'opportunity_type': 'cross_team_coordination'
                        }
                    })
        
        return opportunities
    
    def _calculate_team_complementarity(self, patterns1: List[Dict[str, Any]], patterns2: List[Dict[str, Any]]) -> float:
        """Calculate complementarity between team patterns"""
        # Simple complementarity based on different symbols/timeframes
        if not patterns1 or not patterns2:
            return 0.0
        
        symbols1 = set(p.get('symbol', '') for p in patterns1)
        symbols2 = set(p.get('symbol', '') for p in patterns2)
        
        timeframes1 = set(p.get('timeframe', '') for p in patterns1)
        timeframes2 = set(p.get('timeframe', '') for p in patterns2)
        
        # Complementarity is higher when teams cover different areas
        symbol_overlap = len(symbols1.intersection(symbols2)) / len(symbols1.union(symbols2)) if symbols1.union(symbols2) else 0
        timeframe_overlap = len(timeframes1.intersection(timeframes2)) / len(timeframes1.union(timeframes2)) if timeframes1.union(timeframes2) else 0
        
        # Lower overlap = higher complementarity
        complementarity = 1.0 - (symbol_overlap + timeframe_overlap) / 2.0
        
        return complementarity
    
    async def _publish_meta_signal(self, signal: MetaSignal) -> bool:
        """Publish meta-signal to database"""
        try:
            strand_data = {
                'id': signal.signal_id,
                'module': 'alpha',
                'kind': 'meta_signal',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': [f"agent:central_intelligence:meta_signal_generator:{signal.signal_type}"],
                'created_at': signal.created_at.isoformat(),
                'updated_at': signal.created_at.isoformat(),
                
                # Meta-signal specific data
                'module_intelligence': {
                    'signal_type': signal.signal_type,
                    'source_agents': signal.source_agents,
                    'target_agents': signal.target_agents,
                    'confidence': signal.confidence,
                    'evidence': signal.evidence,
                    'expires_at': signal.expires_at.isoformat() if signal.expires_at else None
                },
                
                # CIL fields
                'cil_team_member': 'meta_signal_generator',
                'strategic_meta_type': signal.signal_type,
                'doctrine_status': 'active',
                
                # Scoring
                'sig_sigma': signal.confidence,
                'sig_confidence': signal.confidence,
                'accumulated_score': signal.confidence
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing meta-signal: {e}")
            return False
