"""
Confluence Detector - A∧B within Δt detection
Detects when multiple agents find similar patterns within a time window
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager


@dataclass
class ConfluenceEvent:
    """Confluence event data structure"""
    event_id: str
    agents: List[str]
    pattern_type: str
    confidence: float
    time_window: timedelta
    evidence: Dict[str, Any]
    created_at: datetime


class ConfluenceDetector:
    """
    Detects confluence events: multiple agents detecting similar patterns within time window
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.default_time_window = timedelta(minutes=5)
        self.confluence_threshold = 0.6
        self.min_agents = 2
    
    async def detect_confluence_events(self, 
                                     time_window_minutes: int = 60,
                                     confluence_window_minutes: int = 5) -> List[ConfluenceEvent]:
        """
        Detect confluence events in recent activity
        
        Args:
            time_window_minutes: How far back to look for patterns
            confluence_window_minutes: Time window for confluence detection
            
        Returns:
            List of detected confluence events
        """
        try:
            # Get recent strands
            recent_strands = await self._get_recent_strands(time_window_minutes)
            
            if len(recent_strands) < self.min_agents:
                return []
            
            # Group strands by time buckets
            time_buckets = self._group_strands_by_time_buckets(
                recent_strands, 
                bucket_minutes=confluence_window_minutes
            )
            
            # Detect confluence in each time bucket
            confluence_events = []
            for bucket_time, bucket_strands in time_buckets.items():
                if len(bucket_strands) < self.min_agents:
                    continue
                
                bucket_confluence = await self._detect_bucket_confluence(bucket_time, bucket_strands)
                confluence_events.extend(bucket_confluence)
            
            # Publish confluence events
            for event in confluence_events:
                await self._publish_confluence_event(event)
            
            return confluence_events
            
        except Exception as e:
            print(f"Error detecting confluence events: {e}")
            return []
    
    async def _get_recent_strands(self, time_window_minutes: int) -> List[Dict[str, Any]]:
        """Get recent strands from all agents"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
            
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= %s 
                AND tags IS NOT NULL
                AND kind != 'uncertainty'
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time.isoformat()])
            return result if result else []
            
        except Exception as e:
            print(f"Error getting recent strands: {e}")
            return []
    
    def _group_strands_by_time_buckets(self, 
                                     strands: List[Dict[str, Any]], 
                                     bucket_minutes: int = 5) -> Dict[datetime, List[Dict[str, Any]]]:
        """Group strands into time buckets"""
        buckets = {}
        
        for strand in strands:
            try:
                created_at = datetime.fromisoformat(strand.get('created_at', '').replace('Z', '+00:00'))
                bucket_time = created_at.replace(
                    minute=(created_at.minute // bucket_minutes) * bucket_minutes, 
                    second=0, 
                    microsecond=0
                )
                
                if bucket_time not in buckets:
                    buckets[bucket_time] = []
                buckets[bucket_time].append(strand)
                
            except Exception as e:
                print(f"Error parsing strand timestamp: {e}")
                continue
        
        return buckets
    
    async def _detect_bucket_confluence(self, 
                                      bucket_time: datetime, 
                                      bucket_strands: List[Dict[str, Any]]) -> List[ConfluenceEvent]:
        """Detect confluence events within a time bucket"""
        confluence_events = []
        
        try:
            # Extract agent patterns from bucket strands
            agent_patterns = self._extract_agent_patterns(bucket_strands)
            
            if len(agent_patterns) < self.min_agents:
                return []
            
            # Find confluence candidates
            confluence_candidates = self._find_confluence_candidates(agent_patterns)
            
            # Create confluence events
            for candidate in confluence_candidates:
                if candidate['confidence'] >= self.confluence_threshold:
                    event = ConfluenceEvent(
                        event_id=f"confluence_{int(bucket_time.timestamp())}_{len(confluence_events)}",
                        agents=candidate['agents'],
                        pattern_type=candidate['pattern_type'],
                        confidence=candidate['confidence'],
                        time_window=timedelta(minutes=5),
                        evidence=candidate['evidence'],
                        created_at=datetime.now(timezone.utc)
                    )
                    confluence_events.append(event)
            
            return confluence_events
            
        except Exception as e:
            print(f"Error detecting bucket confluence: {e}")
            return []
    
    def _extract_agent_patterns(self, strands: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract patterns by agent"""
        agent_patterns = {}
        
        for strand in strands:
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
        candidates = []
        
        agents = list(agent_patterns.keys())
        
        # Check all pairs of agents for confluence
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                agent1, agent2 = agents[i], agents[j]
                patterns1, patterns2 = agent_patterns[agent1], agent_patterns[agent2]
                
                # Calculate confluence between these two agents
                confluence = self._calculate_agent_confluence(agent1, patterns1, agent2, patterns2)
                
                if confluence:
                    candidates.append(confluence)
        
        # Check for multi-agent confluence (3+ agents)
        if len(agents) >= 3:
            multi_agent_confluence = self._find_multi_agent_confluence(agent_patterns)
            candidates.extend(multi_agent_confluence)
        
        return candidates
    
    def _calculate_agent_confluence(self, 
                                  agent1: str, 
                                  patterns1: List[Dict[str, Any]], 
                                  agent2: str, 
                                  patterns2: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Calculate confluence between two agents"""
        if not patterns1 or not patterns2:
            return None
        
        # Calculate pattern similarity
        similarity = self._calculate_pattern_similarity(patterns1, patterns2)
        
        if similarity < self.confluence_threshold:
            return None
        
        # Determine pattern type
        pattern_type = self._determine_confluence_pattern_type(patterns1, patterns2)
        
        # Calculate confidence based on similarity and pattern strength
        confidence = self._calculate_confluence_confidence(patterns1, patterns2, similarity)
        
        return {
            'agents': [agent1, agent2],
            'pattern_type': pattern_type,
            'confidence': confidence,
            'evidence': {
                'agent1_patterns': len(patterns1),
                'agent2_patterns': len(patterns2),
                'similarity_score': similarity,
                'pattern_strength': self._calculate_pattern_strength(patterns1 + patterns2),
                'common_features': self._find_common_features(patterns1, patterns2)
            }
        }
    
    def _calculate_pattern_similarity(self, patterns1: List[Dict[str, Any]], patterns2: List[Dict[str, Any]]) -> float:
        """Calculate similarity between two sets of patterns"""
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
            # Add basic features
            features.add(f"symbol:{pattern.get('symbol', 'unknown')}")
            features.add(f"timeframe:{pattern.get('timeframe', 'unknown')}")
            features.add(f"regime:{pattern.get('regime', 'unknown')}")
            features.add(f"session:{pattern.get('session_bucket', 'unknown')}")
            
            # Add pattern-specific features
            module_intel = pattern.get('module_intelligence', {})
            if isinstance(module_intel, dict):
                # Add pattern type if available
                pattern_type = module_intel.get('pattern_type', 'unknown')
                features.add(f"pattern_type:{pattern_type}")
                
                # Add signal strength if available
                signal_strength = module_intel.get('signal_strength', 'unknown')
                features.add(f"signal_strength:{signal_strength}")
            
            # Add tags as features
            tags = pattern.get('tags', [])
            for tag in tags:
                if ':' in tag:
                    features.add(f"tag:{tag}")
        
        return features
    
    def _determine_confluence_pattern_type(self, patterns1: List[Dict[str, Any]], patterns2: List[Dict[str, Any]]) -> str:
        """Determine the type of confluence pattern"""
        all_patterns = patterns1 + patterns2
        
        # Count pattern types
        pattern_types = {}
        for pattern in all_patterns:
            module_intel = pattern.get('module_intelligence', {})
            if isinstance(module_intel, dict):
                pattern_type = module_intel.get('pattern_type', 'unknown')
                pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
        
        # Return most common pattern type
        if pattern_types:
            return max(pattern_types, key=pattern_types.get)
        
        # Fallback to symbol-based classification
        symbols = set(p.get('symbol', 'unknown') for p in all_patterns)
        if len(symbols) == 1:
            return f"single_asset_{list(symbols)[0]}"
        else:
            return "multi_asset_confluence"
    
    def _calculate_confluence_confidence(self, 
                                       patterns1: List[Dict[str, Any]], 
                                       patterns2: List[Dict[str, Any]], 
                                       similarity: float) -> float:
        """Calculate confidence in confluence detection"""
        # Base confidence from similarity
        confidence = similarity
        
        # Boost confidence for stronger patterns
        pattern_strength = self._calculate_pattern_strength(patterns1 + patterns2)
        confidence += pattern_strength * 0.2
        
        # Boost confidence for more patterns
        total_patterns = len(patterns1) + len(patterns2)
        pattern_count_boost = min(total_patterns / 10.0, 0.3)  # Cap at 0.3
        confidence += pattern_count_boost
        
        # Boost confidence for recent patterns
        recency_boost = self._calculate_recency_boost(patterns1 + patterns2)
        confidence += recency_boost
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _calculate_pattern_strength(self, patterns: List[Dict[str, Any]]) -> float:
        """Calculate overall pattern strength"""
        if not patterns:
            return 0.0
        
        total_strength = 0.0
        for pattern in patterns:
            # Use sig_sigma as pattern strength
            strength = pattern.get('sig_sigma', 0.0)
            if isinstance(strength, (int, float)):
                total_strength += strength
        
        return total_strength / len(patterns)
    
    def _calculate_recency_boost(self, patterns: List[Dict[str, Any]]) -> float:
        """Calculate recency boost for patterns"""
        if not patterns:
            return 0.0
        
        now = datetime.now(timezone.utc)
        total_boost = 0.0
        
        for pattern in patterns:
            try:
                created_at = datetime.fromisoformat(pattern.get('created_at', '').replace('Z', '+00:00'))
                age_minutes = (now - created_at).total_seconds() / 60.0
                
                # Recent patterns get higher boost
                if age_minutes < 5:
                    boost = 0.1
                elif age_minutes < 15:
                    boost = 0.05
                else:
                    boost = 0.0
                
                total_boost += boost
                
            except Exception as e:
                print(f"Error calculating recency boost: {e}")
                continue
        
        return min(total_boost, 0.2)  # Cap at 0.2
    
    def _find_common_features(self, patterns1: List[Dict[str, Any]], patterns2: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find common features between pattern sets"""
        features1 = self._extract_pattern_features(patterns1)
        features2 = self._extract_pattern_features(patterns2)
        
        common_features = features1.intersection(features2)
        
        return {
            'common_count': len(common_features),
            'total_features': len(features1.union(features2)),
            'common_features': list(common_features)
        }
    
    def _find_multi_agent_confluence(self, agent_patterns: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find confluence involving 3+ agents"""
        multi_agent_confluence = []
        
        agents = list(agent_patterns.keys())
        
        # Check all combinations of 3+ agents
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                for k in range(j + 1, len(agents)):
                    agent1, agent2, agent3 = agents[i], agents[j], agents[k]
                    patterns1 = agent_patterns[agent1]
                    patterns2 = agent_patterns[agent2]
                    patterns3 = agent_patterns[agent3]
                    
                    # Calculate multi-agent confluence
                    confluence = self._calculate_multi_agent_confluence(
                        [agent1, agent2, agent3],
                        [patterns1, patterns2, patterns3]
                    )
                    
                    if confluence:
                        multi_agent_confluence.append(confluence)
        
        return multi_agent_confluence
    
    def _calculate_multi_agent_confluence(self, 
                                        agents: List[str], 
                                        pattern_sets: List[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """Calculate confluence for 3+ agents"""
        if len(agents) != len(pattern_sets):
            return None
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(agents)):
            for j in range(i + 1, len(agents)):
                similarity = self._calculate_pattern_similarity(pattern_sets[i], pattern_sets[j])
                similarities.append(similarity)
        
        if not similarities:
            return None
        
        # Multi-agent confluence requires high average similarity
        avg_similarity = sum(similarities) / len(similarities)
        
        if avg_similarity < self.confluence_threshold:
            return None
        
        # Calculate confidence
        confidence = avg_similarity
        total_patterns = sum(len(patterns) for patterns in pattern_sets)
        pattern_count_boost = min(total_patterns / 15.0, 0.3)  # Cap at 0.3
        confidence += pattern_count_boost
        
        return {
            'agents': agents,
            'pattern_type': 'multi_agent_confluence',
            'confidence': min(confidence, 1.0),
            'evidence': {
                'agent_count': len(agents),
                'total_patterns': total_patterns,
                'avg_similarity': avg_similarity,
                'pairwise_similarities': similarities,
                'confluence_strength': 'high' if avg_similarity > 0.8 else 'medium'
            }
        }
    
    async def _publish_confluence_event(self, event: ConfluenceEvent) -> bool:
        """Publish confluence event to database"""
        try:
            strand_data = {
                'id': event.event_id,
                'module': 'alpha',
                'kind': 'confluence_event',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:confluence_detector:confluence_detected'],
                'created_at': event.created_at.isoformat(),
                'updated_at': event.created_at.isoformat(),
                
                # Confluence-specific data
                'module_intelligence': {
                    'event_type': 'confluence_detection',
                    'agents': event.agents,
                    'pattern_type': event.pattern_type,
                    'confidence': event.confidence,
                    'time_window_minutes': event.time_window.total_seconds() / 60.0,
                    'evidence': event.evidence
                },
                
                # CIL fields
                'cil_team_member': 'confluence_detector',
                'strategic_meta_type': 'confluence_event',
                'doctrine_status': 'active',
                
                # Scoring
                'sig_sigma': event.confidence,
                'sig_confidence': event.confidence,
                'accumulated_score': event.confidence
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing confluence event: {e}")
            return False

