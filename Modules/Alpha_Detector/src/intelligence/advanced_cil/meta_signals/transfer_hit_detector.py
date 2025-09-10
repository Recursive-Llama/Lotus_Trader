"""
Transfer Hit Detector - Cross-asset/session motif generalization
Detects when patterns generalize across different assets, sessions, or contexts
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from src.utils.supabase_manager import SupabaseManager


@dataclass
class TransferHit:
    """Transfer hit data structure"""
    transfer_id: str
    source_context: Dict[str, Any]
    target_context: Dict[str, Any]
    pattern_type: str
    confidence: float
    transfer_strength: float
    evidence: Dict[str, Any]
    created_at: datetime


class TransferHitDetector:
    """
    Detects transfer hits: patterns generalizing across assets/sessions/contexts
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.min_transfer_instances = 2
        self.transfer_threshold = 0.6
        self.context_similarity_threshold = 0.4
    
    async def detect_transfer_hits(self, time_window_hours: int = 48) -> List[TransferHit]:
        """
        Detect transfer hits in recent activity
        
        Args:
            time_window_hours: How far back to look for patterns
            
        Returns:
            List of detected transfer hits
        """
        try:
            # Get recent strands
            recent_strands = await self._get_recent_strands(time_window_hours)
            
            if len(recent_strands) < self.min_transfer_instances:
                return []
            
            # Group strands by pattern similarity
            pattern_groups = self._group_strands_by_pattern_similarity(recent_strands)
            
            # Detect transfer hits within each pattern group
            transfer_hits = []
            for pattern_group in pattern_groups:
                if len(pattern_group) >= self.min_transfer_instances:
                    group_transfers = self._detect_group_transfers(pattern_group)
                    transfer_hits.extend(group_transfers)
            
            # Publish transfer hits
            for transfer in transfer_hits:
                await self._publish_transfer_hit(transfer)
            
            return transfer_hits
            
        except Exception as e:
            print(f"Error detecting transfer hits: {e}")
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
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time.isoformat()])
            return result if result else []
            
        except Exception as e:
            print(f"Error getting recent strands: {e}")
            return []
    
    def _group_strands_by_pattern_similarity(self, strands: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group strands by pattern similarity"""
        pattern_groups = []
        processed_strands = set()
        
        for i, strand1 in enumerate(strands):
            if i in processed_strands:
                continue
            
            # Start a new pattern group
            current_group = [strand1]
            processed_strands.add(i)
            
            # Find similar strands
            for j, strand2 in enumerate(strands[i+1:], i+1):
                if j in processed_strands:
                    continue
                
                similarity = self._calculate_pattern_similarity(strand1, strand2)
                if similarity >= self.context_similarity_threshold:
                    current_group.append(strand2)
                    processed_strands.add(j)
            
            if len(current_group) >= self.min_transfer_instances:
                pattern_groups.append(current_group)
        
        return pattern_groups
    
    def _calculate_pattern_similarity(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> float:
        """Calculate pattern similarity between two strands"""
        similarity_score = 0.0
        total_features = 0
        
        # Pattern type similarity (most important)
        pattern_type1 = self._extract_pattern_type(strand1)
        pattern_type2 = self._extract_pattern_type(strand2)
        if pattern_type1 and pattern_type2:
            if pattern_type1 == pattern_type2:
                similarity_score += 2.0  # Double weight for pattern type
            total_features += 2
        elif pattern_type1 or pattern_type2:
            total_features += 2
        
        # Tag similarity
        tags1 = set(strand1.get('tags', []))
        tags2 = set(strand2.get('tags', []))
        if tags1 and tags2:
            tag_similarity = len(tags1.intersection(tags2)) / len(tags1.union(tags2))
            similarity_score += tag_similarity
            total_features += 1
        
        # Module intelligence similarity
        module_intel1 = strand1.get('module_intelligence', {})
        module_intel2 = strand2.get('module_intelligence', {})
        if isinstance(module_intel1, dict) and isinstance(module_intel2, dict):
            module_similarity = self._calculate_module_intelligence_similarity(module_intel1, module_intel2)
            similarity_score += module_similarity
            total_features += 1
        
        # Signal strength similarity
        sig1 = strand1.get('sig_sigma', 0.0)
        sig2 = strand2.get('sig_sigma', 0.0)
        if isinstance(sig1, (int, float)) and isinstance(sig2, (int, float)):
            strength_diff = abs(sig1 - sig2)
            strength_similarity = max(0.0, 1.0 - strength_diff)
            similarity_score += strength_similarity
            total_features += 1
        
        return similarity_score / total_features if total_features > 0 else 0.0
    
    def _extract_pattern_type(self, strand: Dict[str, Any]) -> Optional[str]:
        """Extract pattern type from strand"""
        module_intel = strand.get('module_intelligence', {})
        if isinstance(module_intel, dict):
            return module_intel.get('pattern_type')
        
        # Fallback: extract from tags
        tags = strand.get('tags', [])
        for tag in tags:
            if ':' in tag and any(ptype in tag.lower() for ptype in ['divergence', 'volume', 'correlation', 'pattern']):
                return tag.split(':')[-1]
        
        return None
    
    def _calculate_module_intelligence_similarity(self, module_intel1: Dict[str, Any], module_intel2: Dict[str, Any]) -> float:
        """Calculate similarity between module intelligence data"""
        similarity_score = 0.0
        total_features = 0
        
        # Compare common keys
        common_keys = set(module_intel1.keys()).intersection(set(module_intel2.keys()))
        
        for key in common_keys:
            val1, val2 = module_intel1[key], module_intel2[key]
            
            if isinstance(val1, str) and isinstance(val2, str):
                if val1 == val2:
                    similarity_score += 1.0
                total_features += 1
            elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                diff = abs(val1 - val2)
                max_val = max(abs(val1), abs(val2), 1.0)
                similarity = max(0.0, 1.0 - diff / max_val)
                similarity_score += similarity
                total_features += 1
            elif isinstance(val1, list) and isinstance(val2, list):
                if val1 == val2:
                    similarity_score += 1.0
                else:
                    # Calculate list similarity
                    set1, set2 = set(val1), set(val2)
                    if set1 and set2:
                        list_similarity = len(set1.intersection(set2)) / len(set1.union(set2))
                        similarity_score += list_similarity
                total_features += 1
        
        return similarity_score / total_features if total_features > 0 else 0.0
    
    def _detect_group_transfers(self, pattern_group: List[Dict[str, Any]]) -> List[TransferHit]:
        """Detect transfer hits within a pattern group"""
        transfer_hits = []
        
        # Group by context (symbol, session, regime)
        context_groups = self._group_by_context(pattern_group)
        
        if len(context_groups) < 2:
            return []  # Need at least 2 different contexts for transfer
        
        # Find transfer pairs between contexts
        contexts = list(context_groups.keys())
        
        for i in range(len(contexts)):
            for j in range(i + 1, len(contexts)):
                context1, context2 = contexts[i], contexts[j]
                strands1, strands2 = context_groups[context1], context_groups[context2]
                
                # Calculate transfer strength
                transfer_strength = self._calculate_transfer_strength(strands1, strands2, context1, context2)
                
                if transfer_strength >= self.transfer_threshold:
                    # Determine pattern type
                    pattern_type = self._determine_transfer_pattern_type(strands1 + strands2)
                    
                    # Calculate confidence
                    confidence = self._calculate_transfer_confidence(strands1, strands2, transfer_strength)
                    
                    # Create transfer hit
                    transfer = TransferHit(
                        transfer_id=f"transfer_{context1['symbol']}_{context2['symbol']}_{int(datetime.now().timestamp())}",
                        source_context=context1,
                        target_context=context2,
                        pattern_type=pattern_type,
                        confidence=confidence,
                        transfer_strength=transfer_strength,
                        evidence={
                            'source_instances': len(strands1),
                            'target_instances': len(strands2),
                            'total_instances': len(strands1) + len(strands2),
                            'context_difference': self._calculate_context_difference(context1, context2),
                            'pattern_consistency': self._calculate_pattern_consistency(strands1 + strands2),
                            'time_span': self._calculate_transfer_time_span(strands1 + strands2)
                        },
                        created_at=datetime.now(timezone.utc)
                    )
                    transfer_hits.append(transfer)
        
        return transfer_hits
    
    def _group_by_context(self, strands: List[Dict[str, Any]]) -> Dict[Dict[str, Any], List[Dict[str, Any]]]:
        """Group strands by context (symbol, session, regime)"""
        context_groups = defaultdict(list)
        
        for strand in strands:
            context = {
                'symbol': strand.get('symbol', 'unknown'),
                'session_bucket': strand.get('session_bucket', 'unknown'),
                'regime': strand.get('regime', 'unknown'),
                'timeframe': strand.get('timeframe', 'unknown')
            }
            
            # Use tuple as key for grouping
            context_key = tuple(sorted(context.items()))
            context_groups[context_key].append(strand)
        
        # Convert back to dict with context tuple as key
        result = {}
        for context_tuple, strand_list in context_groups.items():
            result[context_tuple] = strand_list
        
        return result
    
    def _calculate_transfer_strength(self, 
                                   source_strands: List[Dict[str, Any]], 
                                   target_strands: List[Dict[str, Any]], 
                                   source_context: Dict[str, Any], 
                                   target_context: Dict[str, Any]) -> float:
        """Calculate transfer strength between two contexts"""
        # Base strength from pattern similarity
        pattern_similarity = self._calculate_pattern_similarity(source_strands[0], target_strands[0])
        
        # Boost for more instances in each context
        instance_boost = min(len(source_strands) + len(target_strands), 10) / 10.0 * 0.3
        
        # Boost for different contexts (higher difference = stronger transfer)
        context_difference = self._calculate_context_difference(source_context, target_context)
        context_boost = context_difference * 0.2
        
        # Boost for pattern consistency within each context
        source_consistency = self._calculate_pattern_consistency(source_strands)
        target_consistency = self._calculate_pattern_consistency(target_strands)
        consistency_boost = (source_consistency + target_consistency) / 2.0 * 0.2
        
        transfer_strength = pattern_similarity + instance_boost + context_boost + consistency_boost
        
        return min(transfer_strength, 1.0)  # Cap at 1.0
    
    def _calculate_context_difference(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> float:
        """Calculate difference between two contexts"""
        differences = 0
        total_features = 0
        
        for key in ['symbol', 'session_bucket', 'regime', 'timeframe']:
            if context1.get(key) != context2.get(key):
                differences += 1
            total_features += 1
        
        return differences / total_features if total_features > 0 else 0.0
    
    def _calculate_pattern_consistency(self, strands: List[Dict[str, Any]]) -> float:
        """Calculate pattern consistency within a group of strands"""
        if len(strands) < 2:
            return 1.0
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(strands)):
            for j in range(i + 1, len(strands)):
                similarity = self._calculate_pattern_similarity(strands[i], strands[j])
                similarities.append(similarity)
        
        if not similarities:
            return 0.0
        
        return sum(similarities) / len(similarities)
    
    def _calculate_transfer_time_span(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate time span of transfer observations"""
        if not strands:
            return {'span_hours': 0, 'span_minutes': 0}
        
        times = []
        for strand in strands:
            try:
                created_at = datetime.fromisoformat(strand.get('created_at', '').replace('Z', '+00:00'))
                times.append(created_at)
            except Exception as e:
                print(f"Error parsing strand timestamp: {e}")
                continue
        
        if not times:
            return {'span_hours': 0, 'span_minutes': 0}
        
        earliest = min(times)
        latest = max(times)
        span = latest - earliest
        
        return {
            'span_hours': span.total_seconds() / 3600.0,
            'span_minutes': span.total_seconds() / 60.0,
            'earliest': earliest.isoformat(),
            'latest': latest.isoformat()
        }
    
    def _determine_transfer_pattern_type(self, strands: List[Dict[str, Any]]) -> str:
        """Determine the type of transfer pattern"""
        # Count pattern types
        pattern_types = defaultdict(int)
        
        for strand in strands:
            pattern_type = self._extract_pattern_type(strand)
            if pattern_type:
                pattern_types[pattern_type] += 1
        
        if pattern_types:
            # Return most common pattern type
            most_common = max(pattern_types, key=pattern_types.get)
            return f"transfer_{most_common}"
        
        # Fallback: determine from context differences
        symbols = set(strand.get('symbol', 'unknown') for strand in strands)
        sessions = set(strand.get('session_bucket', 'unknown') for strand in strands)
        regimes = set(strand.get('regime', 'unknown') for strand in strands)
        
        if len(symbols) > 1:
            return "cross_asset_transfer"
        elif len(sessions) > 1:
            return "cross_session_transfer"
        elif len(regimes) > 1:
            return "cross_regime_transfer"
        else:
            return "context_transfer"
    
    def _calculate_transfer_confidence(self, 
                                     source_strands: List[Dict[str, Any]], 
                                     target_strands: List[Dict[str, Any]], 
                                     transfer_strength: float) -> float:
        """Calculate confidence in transfer detection"""
        # Base confidence from transfer strength
        confidence = transfer_strength
        
        # Boost for more instances
        total_instances = len(source_strands) + len(target_strands)
        instance_boost = min(total_instances / 8.0, 0.3)  # Cap at 0.3
        confidence += instance_boost
        
        # Boost for pattern consistency
        source_consistency = self._calculate_pattern_consistency(source_strands)
        target_consistency = self._calculate_pattern_consistency(target_strands)
        consistency_boost = (source_consistency + target_consistency) / 2.0 * 0.2
        confidence += consistency_boost
        
        # Boost for signal strength
        avg_signal_strength = 0.0
        all_strands = source_strands + target_strands
        for strand in all_strands:
            sig_strength = strand.get('sig_sigma', 0.0)
            if isinstance(sig_strength, (int, float)):
                avg_signal_strength += sig_strength
        
        if all_strands:
            avg_signal_strength /= len(all_strands)
            signal_boost = avg_signal_strength * 0.1
            confidence += signal_boost
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    async def _publish_transfer_hit(self, transfer: TransferHit) -> bool:
        """Publish transfer hit to database"""
        try:
            strand_data = {
                'id': transfer.transfer_id,
                'module': 'alpha',
                'kind': 'transfer_hit',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:transfer_hit_detector:transfer_detected'],
                'created_at': transfer.created_at.isoformat(),
                'updated_at': transfer.created_at.isoformat(),
                
                # Transfer-specific data
                'module_intelligence': {
                    'transfer_type': 'cross_context_generalization',
                    'source_context': transfer.source_context,
                    'target_context': transfer.target_context,
                    'pattern_type': transfer.pattern_type,
                    'confidence': transfer.confidence,
                    'transfer_strength': transfer.transfer_strength,
                    'evidence': transfer.evidence
                },
                
                # CIL fields
                'team_member': 'transfer_hit_detector',
                'strategic_meta_type': 'transfer_hit',
                'doctrine_status': 'active',
                
                # Scoring
                'sig_sigma': transfer.confidence,
                'sig_confidence': transfer.confidence,
                'accumulated_score': transfer.confidence
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing transfer hit: {e}")
            return False
