"""
Lead-Lag Predictor - A→B motif detection
Detects when one agent consistently fires before another, suggesting lead-lag relationships
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from src.utils.supabase_manager import SupabaseManager


@dataclass
class LeadLagRelationship:
    """Lead-lag relationship data structure"""
    relationship_id: str
    lead_agent: str
    lag_agent: str
    confidence: float
    avg_lag_seconds: float
    consistency_score: float
    evidence: Dict[str, Any]
    created_at: datetime


class LeadLagPredictor:
    """
    Detects lead-lag relationships: one agent consistently firing before another
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.min_observations = 3
        self.max_lag_seconds = 300  # 5 minutes
        self.consistency_threshold = 0.7
        self.confidence_threshold = 0.6
    
    async def detect_lead_lag_relationships(self, time_window_hours: int = 24) -> List[LeadLagRelationship]:
        """
        Detect lead-lag relationships in recent activity
        
        Args:
            time_window_hours: How far back to look for patterns
            
        Returns:
            List of detected lead-lag relationships
        """
        try:
            # Get recent strands
            recent_strands = await self._get_recent_strands(time_window_hours)
            
            if len(recent_strands) < 2:
                return []
            
            # Build agent sequences
            agent_sequences = self._build_agent_sequences(recent_strands)
            
            if len(agent_sequences) < 2:
                return []
            
            # Detect lead-lag relationships
            relationships = self._detect_relationships(agent_sequences)
            
            # Publish relationships
            for relationship in relationships:
                await self._publish_lead_lag_relationship(relationship)
            
            return relationships
            
        except Exception as e:
            print(f"Error detecting lead-lag relationships: {e}")
            return []
    
    async def _get_recent_strands(self, time_window_hours: int) -> List[Dict[str, Any]]:
        """Get recent strands from all agents"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
            
            query = """
                SELECT * FROM AD_strands 
                WHERE created_at >= %s 
                AND tags IS NOT NULL
                AND kind != 'uncertainty'
                ORDER BY created_at ASC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time.isoformat()])
            return result if result else []
            
        except Exception as e:
            print(f"Error getting recent strands: {e}")
            return []
    
    def _build_agent_sequences(self, strands: List[Dict[str, Any]]) -> Dict[str, List[Tuple[datetime, Dict[str, Any]]]]:
        """Build sequences of agent activity with timestamps and strand data"""
        agent_sequences = defaultdict(list)
        
        for strand in strands:
            try:
                agent = self._extract_agent_from_tags(strand.get('tags', []))
                if agent:
                    created_at = datetime.fromisoformat(strand.get('created_at', '').replace('Z', '+00:00'))
                    agent_sequences[agent].append((created_at, strand))
                    
            except Exception as e:
                print(f"Error building agent sequence: {e}")
                continue
        
        # Sort sequences by time
        for agent in agent_sequences:
            agent_sequences[agent].sort(key=lambda x: x[0])
        
        return dict(agent_sequences)
    
    def _extract_agent_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract agent name from tags"""
        for tag in tags:
            if 'agent:' in tag:
                parts = tag.split(':')
                if len(parts) >= 2:
                    return parts[1]  # Return agent name
        return None
    
    def _detect_relationships(self, agent_sequences: Dict[str, List[Tuple[datetime, Dict[str, Any]]]]) -> List[LeadLagRelationship]:
        """Detect lead-lag relationships between agents"""
        relationships = []
        
        agents = list(agent_sequences.keys())
        
        # Check all pairs of agents
        for i in range(len(agents)):
            for j in range(len(agents)):
                if i == j:
                    continue
                
                agent1, agent2 = agents[i], agents[j]
                sequence1, sequence2 = agent_sequences[agent1], agent_sequences[agent2]
                
                # Check if agent1 leads agent2
                relationship = self._analyze_lead_lag(agent1, sequence1, agent2, sequence2)
                
                if relationship and relationship.confidence >= self.confidence_threshold:
                    relationships.append(relationship)
        
        return relationships
    
    def _analyze_lead_lag(self, 
                         lead_agent: str, 
                         lead_sequence: List[Tuple[datetime, Dict[str, Any]]], 
                         lag_agent: str, 
                         lag_sequence: List[Tuple[datetime, Dict[str, Any]]]) -> Optional[LeadLagRelationship]:
        """Analyze lead-lag relationship between two agents"""
        if not lead_sequence or not lag_sequence:
            return None
        
        # Find all lead-lag pairs within time window
        lead_lag_pairs = []
        
        for lead_time, lead_strand in lead_sequence:
            for lag_time, lag_strand in lag_sequence:
                time_diff = (lag_time - lead_time).total_seconds()
                
                # Check if lag follows lead within acceptable window
                if 0 < time_diff <= self.max_lag_seconds:
                    # Check for pattern similarity
                    similarity = self._calculate_strand_similarity(lead_strand, lag_strand)
                    
                    if similarity > 0.3:  # Minimum similarity threshold
                        lead_lag_pairs.append({
                            'lead_time': lead_time,
                            'lag_time': lag_time,
                            'lag_seconds': time_diff,
                            'similarity': similarity,
                            'lead_strand': lead_strand,
                            'lag_strand': lag_strand
                        })
        
        if len(lead_lag_pairs) < self.min_observations:
            return None
        
        # Calculate relationship metrics
        avg_lag = sum(pair['lag_seconds'] for pair in lead_lag_pairs) / len(lead_lag_pairs)
        consistency = self._calculate_consistency(lead_lag_pairs)
        confidence = self._calculate_relationship_confidence(lead_lag_pairs, consistency)
        
        if consistency < self.consistency_threshold:
            return None
        
        return LeadLagRelationship(
            relationship_id=f"lead_lag_{lead_agent}_{lag_agent}_{int(datetime.now().timestamp())}",
            lead_agent=lead_agent,
            lag_agent=lag_agent,
            confidence=confidence,
            avg_lag_seconds=avg_lag,
            consistency_score=consistency,
            evidence={
                'total_pairs': len(lead_lag_pairs),
                'avg_similarity': sum(pair['similarity'] for pair in lead_lag_pairs) / len(lead_lag_pairs),
                'lag_range': {
                    'min': min(pair['lag_seconds'] for pair in lead_lag_pairs),
                    'max': max(pair['lag_seconds'] for pair in lead_lag_pairs),
                    'std': self._calculate_std_dev([pair['lag_seconds'] for pair in lead_lag_pairs])
                },
                'pattern_types': self._extract_pattern_types(lead_lag_pairs),
                'time_span': self._calculate_time_span(lead_lag_pairs)
            },
            created_at=datetime.now(timezone.utc)
        )
    
    def _calculate_strand_similarity(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> float:
        """Calculate similarity between two strands"""
        similarity_score = 0.0
        total_features = 0
        
        # Symbol similarity
        if strand1.get('symbol') == strand2.get('symbol'):
            similarity_score += 1.0
        total_features += 1
        
        # Timeframe similarity
        if strand1.get('timeframe') == strand2.get('timeframe'):
            similarity_score += 1.0
        total_features += 1
        
        # Regime similarity
        if strand1.get('regime') == strand2.get('regime'):
            similarity_score += 1.0
        total_features += 1
        
        # Session similarity
        if strand1.get('session_bucket') == strand2.get('session_bucket'):
            similarity_score += 1.0
        total_features += 1
        
        # Pattern type similarity (from module_intelligence)
        pattern_type1 = self._extract_pattern_type(strand1)
        pattern_type2 = self._extract_pattern_type(strand2)
        if pattern_type1 and pattern_type2 and pattern_type1 == pattern_type2:
            similarity_score += 1.0
        total_features += 1
        
        # Tag similarity
        tags1 = set(strand1.get('tags', []))
        tags2 = set(strand2.get('tags', []))
        if tags1 and tags2:
            tag_similarity = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
            similarity_score += tag_similarity
            total_features += 1
        
        return similarity_score / total_features if total_features > 0 else 0.0
    
    def _extract_pattern_type(self, strand: Dict[str, Any]) -> Optional[str]:
        """Extract pattern type from strand"""
        module_intel = strand.get('module_intelligence', {})
        if isinstance(module_intel, dict):
            return module_intel.get('pattern_type')
        return None
    
    def _calculate_consistency(self, lead_lag_pairs: List[Dict[str, Any]]) -> float:
        """Calculate consistency of lead-lag timing"""
        if len(lead_lag_pairs) < 2:
            return 1.0
        
        lag_times = [pair['lag_seconds'] for pair in lead_lag_pairs]
        avg_lag = sum(lag_times) / len(lag_times)
        
        # Calculate coefficient of variation (lower = more consistent)
        if avg_lag == 0:
            return 0.0
        
        std_dev = self._calculate_std_dev(lag_times)
        cv = std_dev / avg_lag
        
        # Convert to consistency score (0-1, higher is more consistent)
        consistency = max(0.0, 1.0 - cv)
        
        return consistency
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _calculate_relationship_confidence(self, lead_lag_pairs: List[Dict[str, Any]], consistency: float) -> float:
        """Calculate confidence in lead-lag relationship"""
        # Base confidence from consistency
        confidence = consistency
        
        # Boost confidence for more observations
        observation_boost = min(len(lead_lag_pairs) / 10.0, 0.3)  # Cap at 0.3
        confidence += observation_boost
        
        # Boost confidence for higher similarity
        avg_similarity = sum(pair['similarity'] for pair in lead_lag_pairs) / len(lead_lag_pairs)
        similarity_boost = avg_similarity * 0.2
        confidence += similarity_boost
        
        # Boost confidence for shorter, more predictable lags
        avg_lag = sum(pair['lag_seconds'] for pair in lead_lag_pairs) / len(lead_lag_pairs)
        if avg_lag < 60:  # Less than 1 minute
            lag_boost = 0.1
        elif avg_lag < 180:  # Less than 3 minutes
            lag_boost = 0.05
        else:
            lag_boost = 0.0
        confidence += lag_boost
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _extract_pattern_types(self, lead_lag_pairs: List[Dict[str, Any]]) -> List[str]:
        """Extract pattern types from lead-lag pairs"""
        pattern_types = set()
        
        for pair in lead_lag_pairs:
            lead_pattern = self._extract_pattern_type(pair['lead_strand'])
            lag_pattern = self._extract_pattern_type(pair['lag_strand'])
            
            if lead_pattern:
                pattern_types.add(f"lead:{lead_pattern}")
            if lag_pattern:
                pattern_types.add(f"lag:{lag_pattern}")
        
        return list(pattern_types)
    
    def _calculate_time_span(self, lead_lag_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time span of lead-lag observations"""
        if not lead_lag_pairs:
            return {'span_hours': 0, 'span_minutes': 0}
        
        times = [pair['lead_time'] for pair in lead_lag_pairs]
        earliest = min(times)
        latest = max(times)
        
        span = latest - earliest
        span_hours = span.total_seconds() / 3600.0
        span_minutes = span.total_seconds() / 60.0
        
        return {
            'span_hours': span_hours,
            'span_minutes': span_minutes,
            'earliest': earliest.isoformat(),
            'latest': latest.isoformat()
        }
    
    async def _publish_lead_lag_relationship(self, relationship: LeadLagRelationship) -> bool:
        """Publish lead-lag relationship to database"""
        try:
            strand_data = {
                'id': relationship.relationship_id,
                'module': 'alpha',
                'kind': 'lead_lag_relationship',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:lead_lag_predictor:relationship_detected'],
                'created_at': relationship.created_at.isoformat(),
                'updated_at': relationship.created_at.isoformat(),
                
                # Lead-lag specific data
                'module_intelligence': {
                    'relationship_type': 'lead_lag_detection',
                    'lead_agent': relationship.lead_agent,
                    'lag_agent': relationship.lag_agent,
                    'confidence': relationship.confidence,
                    'avg_lag_seconds': relationship.avg_lag_seconds,
                    'consistency_score': relationship.consistency_score,
                    'evidence': relationship.evidence
                },
                
                # CIL fields
                'team_member': 'lead_lag_predictor',
                'strategic_meta_type': 'lead_lag_predict',
                'doctrine_status': 'active',
                
                # Scoring
                'sig_sigma': relationship.confidence,
                'sig_confidence': relationship.confidence,
                'accumulated_score': relationship.confidence
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing lead-lag relationship: {e}")
            return False
